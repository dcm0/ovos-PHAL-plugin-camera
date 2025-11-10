import os
from typing import Optional, Iterable
from threading import Thread

import cv2
import numpy as np
import pybase64
from imutils.video import VideoStream

from ovos_bus_client.message import Message
from ovos_bus_client.session import SessionManager
from ovos_plugin_manager.templates.phal import PHALPlugin
from ovos_utils.log import LOG


class Camera:
    def __init__(self, camera_index: int = 0):
        """
        Initialize a Camera object.

        Args:
            camera_index (int): The index of the camera to use. Default is 0.
        """
        self.camera_index: int = camera_index
        self._camera: Optional[VideoStream] = None
        self.camera_type: str = self.detect_camera_type()

    @staticmethod
    def detect_camera_type() -> str:
        """
        Detect the camera type ("libcamera" for Raspberry Pi or "opencv" for other systems).

        Returns:
            str: The detected camera type.
        """
        try:
            import libcamera  # type: ignore
            return "libcamera"
        except ImportError:
            return "opencv"

    @property
    def is_open(self) -> bool:
        """
        Check if the camera is open.

        Returns:
            bool: True if the camera is open, False otherwise.
        """
        return self._camera is not None

    def open(self, force=False) -> Optional[VideoStream]:
        """
        Open the camera based on the detected type.

        Returns:
            Optional[VideoStream]: The initialized camera instance, or None if opening failed.
        """
        if self._camera is not None and not force:
            return self._camera  # do nothing, camera is open already

        if self.camera_type == "libcamera":
            try:
                from picamera2 import Picamera2  # type: ignore
                self._camera = Picamera2()
                self._camera.start()
                LOG.info("libcamera initialized")
            except Exception as e:
                LOG.error(f"Failed to start libcamera: {e}")
                return None
        elif self.camera_type == "opencv":
            try:
                self._camera = VideoStream(self.camera_index)
                if not self._camera.stream.grabbed:
                    self._camera = None
                    raise ValueError("OpenCV Camera stream could not be started")
                self._camera.start()
            except Exception as e:
                LOG.error(f"Failed to start OpenCV camera: {e}")
                return None
        return self._camera

    def get_frame(self) -> np.ndarray:
        """
        Capture a frame from the camera.

        Returns:
            np.ndarray: The captured frame.
        """
        if self.camera_type == "libcamera":
            frame = self._camera.capture_array()  # In RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert RGB to BGR for OpenCV compatibility
            return frame
        else:
            return self._camera.read()

    def close(self) -> None:
        """
        Close the camera.
        """
        if self._camera:
            if self.camera_type == "libcamera":
                self._camera.close()
            elif self.camera_type == "opencv":
                self._camera.stop()
            self._camera = None

    def __enter__(self) -> "Camera":
        """
        Enter the context and open the camera.

        Returns:
            Camera: The Camera instance.

        Raises:
            RuntimeError: If the camera fails to open.
        """
        if self.open() is None:
            raise RuntimeError("Failed to open the camera")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Exit the context and close the camera.
        """
        self.close()


class PHALCamera(PHALPlugin):
    def __init__(self, bus, name: str = "ovos-phal-plugin-camera", config: Optional[dict] = None):
        """
        Initialize a PHALCamera plugin.

        Args:
            bus: The message bus instance.
            name (str): The name of the plugin. Default is "ovos-phal-plugin-camera".
            config (Optional[dict]): Configuration dictionary. Default is None.
        """
        super().__init__(bus, name, config)
        self.camera = Camera(self.config.get("video_source", 0))
        self.bus.on("ovos.phal.camera.ping", self.handle_pong)
        self.bus.on("ovos.phal.camera.open", self.handle_open)
        self.bus.on("ovos.phal.camera.close", self.handle_close)
        self.bus.on("ovos.phal.camera.get", self.handle_take_picture)
        if self.camera.open() is None:
            LOG.error("Camera initialization failed")
            raise RuntimeError("Failed to open camera")
        if not self.config.get("start_open"):
            self.camera.close()  # only opened for the check

        # let the system know we have a camera
        self.bus.emit(Message("ovos.phal.camera.pong"))

    def handle_pong(self, message: Message) -> None:
        """
        Let OVOS know camera is available

        Args:
            message (Message): The incoming message.
        """
        if self.validate_message_context(message):
            self.bus.emit(message.reply("ovos.phal.camera.pong"))

    def handle_open(self, message: Message) -> None:
        """
        Handle the "open camera" message.

        Args:
            message (Message): The incoming message.
        """
        if self.validate_message_context(message):
            self.camera.open()

    def handle_close(self, message: Message) -> None:
        """
        Handle the "close camera" message.

        Args:
            message (Message): The incoming message.
        """
        if self.validate_message_context(message):
            self.camera.close()

    def handle_take_picture(self, message: Message) -> None:
        """
        Handle the "take picture" message.

        Args:
            message (Message): The incoming message.
        """
        if not self.validate_message_context(message):
            return

        LOG.debug(f"Camera open: {self.camera.is_open}")
        if not self.camera.is_open:
            self.camera.open()
            close = True
        else:
            close = False

        frame = self.camera.get_frame()
        pic_path = message.data.get("path")
        if pic_path:
            try:
                pic_path = os.path.expanduser(pic_path)
                # Ensure the directory exists
                os.makedirs(os.path.dirname(pic_path), exist_ok=True)
                # Write the image
                if cv2.imwrite(pic_path, frame):
                    self.bus.emit(message.response({"path": pic_path}))
                else:
                    raise IOError("Failed to write image")
                LOG.info(f"Picture saved: {pic_path}")
            except Exception as e:
                LOG.error(f"Error saving image: {e}")
                self.bus.emit(message.response({"error": str(e)}, False))
        # send data b64 encoded instead
        else:
            self.bus.emit(message.response({"b64_frame": pybase64.b64encode(frame).decode('utf-8')}))

        if close:
            LOG.debug("Closing camera")
            self.camera.close()

    def run(self) -> None:
        """
        Run the plugin. If configured, start the MJPEG server.
        """
        if self.config.get("serve_mjpeg"):
            LOG.info("Starting MJPEG server")
            host = self.config.get("mjpeg_host", "0.0.0.0")
            port = self.config.get("mjpeg_port", 5000)
            LOG.info(f"MJPEG server will listen on {host}:{port}")
            app = MJPEGServer.get_mjpeg_server(self.camera)
            LOG.info("Flask app created, starting server in background thread...")
            
            def run_server():
                try:
                    app.run(
                        host=host,
                        port=port,
                        debug=False,
                        threaded=True,
                        use_reloader=False
                    )
                except Exception as e:
                    LOG.error(f"Failed to start MJPEG server: {e}")
            
            # Start Flask in a daemon thread so it doesn't block PHAL
            server_thread = Thread(target=run_server, daemon=True)
            server_thread.start()
            LOG.info("MJPEG server thread started")
        else:
            LOG.info("MJPEG server not started because config set to " + str(self.config.get("serve_mjpeg")))

    def validate_message_context(self, message):
        sid = SessionManager.get(message).session_id
        LOG.debug(f"Request session: {sid}  |  Native Session: {self.bus.session_id}")
        return sid == self.bus.session_id

    def shutdown(self) -> None:
        """
        Shutdown the plugin and close the camera.
        """
        self.camera.close()


class MJPEGServer:
    @staticmethod
    def gen_frames(camera) -> Iterable[bytes]:  # generate frame by frame from camera
        """Generate frame-by-frame data from the camera."""
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue
            try:
                ret, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            except Exception as e:
                LOG.error(f"Error generating frames: {e}")

    @staticmethod
    def get_mjpeg_server(camera: "Camera") -> "Flask":
        """
        Create an MJPEG server using Flask to stream video frames from the camera.

        Args:
            camera (Camera): The camera instance to stream frames from.

        Returns:
            Flask: A Flask application configured for streaming video.
        """
        from flask import Flask, Response

        app = Flask(__name__)

        @app.route('/video_feed')
        def video_feed() -> Response:
            """Stream video frames over HTTP."""
            return Response(MJPEGServer.gen_frames(camera), content_type='multipart/x-mixed-replace; boundary=frame')

        return app

