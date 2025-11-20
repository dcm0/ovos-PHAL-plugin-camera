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
    def __init__(self, camera_index: int = 0, config: Optional[dict] = None):
        """
        Initialize a Camera object.

        Args:
            camera_index (int): The index of the camera to use. Default is 0.
            config (Optional[dict]): Configuration dictionary for camera settings.
        """
        self.camera_index: int = camera_index
        self._camera: Optional[VideoStream] = None
        self.config: dict = config or {}
        self.camera_type: str = self.detect_camera_type()
        self.camera_model: str = ""
        self.is_ai_camera: bool = False
        self.ai_model_info: dict = {}

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
                
                # Detect camera model and AI capabilities
                self._detect_camera_model()
                
                # Configure camera with user settings if provided
                config_dict = self._build_picamera2_config()
                if config_dict:
                    self._camera.configure(config_dict)
                    LOG.info(f"Configured libcamera with custom settings: {config_dict}")
                
                self._camera.start()
                LOG.info(f"libcamera initialized - Model: {self.camera_model}, AI: {self.is_ai_camera}")
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
                self.camera_model = f"OpenCV Camera {self.camera_index}"
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

    def restart(self) -> bool:
        """
        Restart the camera by closing and reopening it.
        Useful for recovering from errors or applying new settings.
        
        Returns:
            bool: True if restart was successful, False otherwise
        """
        try:
            LOG.info("Restarting camera...")
            was_open = self.is_open
            
            # Close if open
            if was_open:
                self.close()
            
            # Reopen
            result = self.open(force=True)
            
            if result is not None:
                LOG.info("Camera restarted successfully")
                return True
            else:
                LOG.error("Camera restart failed")
                return False
        except Exception as e:
            LOG.error(f"Error restarting camera: {e}")
            return False

    def reset(self) -> dict:
        """
        Reset the camera to default settings and restart.
        
        Returns:
            dict: Status and error information
        """
        try:
            LOG.info("Resetting camera to defaults...")
            
            # Close camera
            self.close()
            
            # Clear configuration (keep only video source)
            video_source = self.config.get("video_source", 0)
            self.config = {"video_source": video_source}
            
            # Clear AI state if AI camera
            if self.is_ai_camera:
                self.ai_model_info = {
                    "loaded": False,
                    "model_name": "",
                    "model_path": "",
                    "inference_enabled": False
                }
            
            # Reopen with defaults
            result = self.open(force=True)
            
            if result is not None:
                LOG.info("Camera reset successfully")
                return {"success": True, "message": "Camera reset to defaults"}
            else:
                return {"success": False, "error": "Failed to reopen camera after reset"}
                
        except Exception as e:
            LOG.error(f"Error resetting camera: {e}")
            return {"success": False, "error": str(e)}

    def _detect_camera_model(self) -> None:
        """Detect the camera model and AI capabilities (for Picamera2)."""
        try:
            if self.camera_type == "libcamera" and self._camera:
                camera_properties = self._camera.camera_properties
                self.camera_model = camera_properties.get('Model', 'Unknown')
                
                # Detect IMX500 AI camera
                if 'imx500' in self.camera_model.lower():
                    self.is_ai_camera = True
                    LOG.info("AI Camera (IMX500) detected")
                    self._detect_ai_model()
        except Exception as e:
            LOG.warning(f"Could not detect camera model: {e}")
            self.camera_model = "Unknown"

    def _detect_ai_model(self) -> None:
        """Detect the current AI model loaded on IMX500."""
        try:
            if self.is_ai_camera and self._camera:
                # IMX500 AI model detection
                from picamera2.devices import IMX500  # type: ignore
                
                # Try to get current model info
                # Note: This is framework-dependent, adjust based on actual IMX500 API
                self.ai_model_info = {
                    "loaded": True,
                    "model_name": "unknown",
                    "model_path": "",
                    "inference_enabled": False
                }
                LOG.info(f"AI model info: {self.ai_model_info}")
        except Exception as e:
            LOG.warning(f"Could not detect AI model: {e}")
            self.ai_model_info = {"loaded": False, "error": str(e)}

    def _build_picamera2_config(self) -> Optional[dict]:
        """Build Picamera2 configuration from user settings."""
        if self.camera_type != "libcamera":
            return None
        
        config_params = {}
        
        # Extract user-defined settings
        width = self.config.get("width")
        height = self.config.get("height")
        fps = self.config.get("fps")
        format = self.config.get("format", "RGB888")
        
        if width and height:
            config_params["main"] = {"size": (width, height)}
            if format:
                config_params["main"]["format"] = format
        
        return config_params if config_params else None

    def update_settings(self, settings: dict) -> bool:
        """
        Update camera settings at runtime.
        
        Args:
            settings: Dictionary of settings to update (width, height, fps, quality, etc.)
            
        Returns:
            bool: True if settings were applied successfully
        """
        try:
            self.config.update(settings)
            
            # For libcamera, need to restart with new config
            if self.camera_type == "libcamera" and self.is_open:
                LOG.info(f"Applying new camera settings: {settings}")
                self.close()
                self.open()
                return True
            
            return True
        except Exception as e:
            LOG.error(f"Failed to update camera settings: {e}")
            return False

    def get_capabilities(self) -> dict:
        """Get camera capabilities and current settings."""
        caps = {
            "camera_type": self.camera_type,
            "camera_model": self.camera_model,
            "is_ai_camera": self.is_ai_camera,
            "is_open": self.is_open,
            "current_settings": self.config.copy(),
        }
        
        if self.is_ai_camera:
            caps["ai_model_info"] = self.ai_model_info
        
        if self.camera_type == "libcamera" and self._camera:
            try:
                # Get available modes/resolutions
                caps["available_modes"] = []
                sensor_modes = self._camera.sensor_modes
                for mode in sensor_modes:
                    caps["available_modes"].append({
                        "size": mode.get("size"),
                        "fps": mode.get("fps"),
                        "format": mode.get("format")
                    })
            except Exception as e:
                LOG.warning(f"Could not get camera modes: {e}")
        
        return caps

    def load_ai_model(self, model_path: str, model_name: str = "") -> dict:
        """
        Load an AI model onto the IMX500 camera.
        
        Args:
            model_path: Path to the model file (.rpk for IMX500)
            model_name: Optional friendly name for the model
            
        Returns:
            dict: Status and model info
        """
        if not self.is_ai_camera:
            return {"success": False, "error": "Not an AI camera"}
        
        try:
            # IMX500 model loading
            # Note: Actual implementation depends on Picamera2/IMX500 API
            from picamera2.devices import IMX500  # type: ignore
            
            if not os.path.exists(model_path):
                return {"success": False, "error": f"Model file not found: {model_path}"}
            
            # Load the model (API-dependent)
            # imx500 = IMX500(self._camera)
            # imx500.load_model(model_path)
            
            self.ai_model_info = {
                "loaded": True,
                "model_name": model_name or os.path.basename(model_path),
                "model_path": model_path,
                "inference_enabled": False
            }
            
            LOG.info(f"AI model loaded: {self.ai_model_info}")
            return {"success": True, "model_info": self.ai_model_info}
            
        except Exception as e:
            LOG.error(f"Failed to load AI model: {e}")
            return {"success": False, "error": str(e)}

    def set_ai_inference(self, enabled: bool) -> dict:
        """
        Enable or disable AI inference on the IMX500.
        
        Args:
            enabled: True to enable inference, False to disable
            
        Returns:
            dict: Status
        """
        if not self.is_ai_camera:
            return {"success": False, "error": "Not an AI camera"}
        
        try:
            # Enable/disable inference (API-dependent)
            self.ai_model_info["inference_enabled"] = enabled
            LOG.info(f"AI inference {'enabled' if enabled else 'disabled'}")
            return {"success": True, "inference_enabled": enabled}
        except Exception as e:
            LOG.error(f"Failed to set AI inference: {e}")
            return {"success": False, "error": str(e)}

    def get_ai_inference(self) -> Optional[dict]:
        """
        Get the latest AI inference results from IMX500.
        
        Returns:
            dict: Inference results or None
        """
        if not self.is_ai_camera or not self.ai_model_info.get("inference_enabled"):
            return None
        
        try:
            # Get inference results (API-dependent)
            # This would return detected objects, classifications, etc.
            # from picamera2.devices import IMX500
            # results = imx500.get_results()
            
            # Placeholder structure
            results = {
                "timestamp": None,
                "detections": [],
                "metadata": {}
            }
            return results
        except Exception as e:
            LOG.error(f"Failed to get AI inference: {e}")
            return None

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
        self.camera = Camera(self.config.get("video_source", 0), self.config)
        self.bus.on("ovos.phal.camera.ping", self.handle_pong)
        self.bus.on("ovos.phal.camera.open", self.handle_open)
        self.bus.on("ovos.phal.camera.close", self.handle_close)
        self.bus.on("ovos.phal.camera.get", self.handle_take_picture)
        
        # New bus message handlers for camera control and AI
        self.bus.on("ovos.phal.camera.info.get", self.handle_get_info)
        self.bus.on("ovos.phal.camera.capabilities.get", self.handle_get_capabilities)
        self.bus.on("ovos.phal.camera.settings.get", self.handle_get_settings)
        self.bus.on("ovos.phal.camera.settings.set", self.handle_set_settings)
        self.bus.on("ovos.phal.camera.restart", self.handle_restart)
        self.bus.on("ovos.phal.camera.reset", self.handle_reset)
        self.bus.on("ovos.phal.camera.ai.model.load", self.handle_ai_load_model)
        self.bus.on("ovos.phal.camera.ai.inference.set", self.handle_ai_set_inference)
        self.bus.on("ovos.phal.camera.ai.inference.get", self.handle_ai_get_inference)
        
        # AI inference monitoring thread
        self.ai_monitoring_thread = None
        self.ai_monitoring_active = False
        
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

    def handle_get_info(self, message: Message) -> None:
        """
        Handle request for camera information.
        
        Response: ovos.phal.camera.info.response
        """
        if not self.validate_message_context(message):
            return
        
        info = {
            "camera_type": self.camera.camera_type,
            "camera_model": self.camera.camera_model,
            "is_ai_camera": self.camera.is_ai_camera,
            "is_open": self.camera.is_open,
            "mjpeg_enabled": self.config.get("serve_mjpeg", False),
            "mjpeg_url": f"http://{self.config.get('mjpeg_host', '0.0.0.0')}:{self.config.get('mjpeg_port', 5000)}/video_feed" if self.config.get("serve_mjpeg") else None
        }
        
        self.bus.emit(message.response(info))
        LOG.debug(f"Camera info sent: {info}")

    def handle_get_capabilities(self, message: Message) -> None:
        """
        Handle request for camera capabilities.
        
        Response: ovos.phal.camera.capabilities.response
        """
        if not self.validate_message_context(message):
            return
        
        capabilities = self.camera.get_capabilities()
        self.bus.emit(message.response(capabilities))
        LOG.debug(f"Camera capabilities sent: {capabilities}")

    def handle_get_settings(self, message: Message) -> None:
        """
        Handle request for current camera settings.
        
        Response: ovos.phal.camera.settings.response
        """
        if not self.validate_message_context(message):
            return
        
        settings = {
            "video_source": self.camera.camera_index,
            "width": self.camera.config.get("width"),
            "height": self.camera.config.get("height"),
            "fps": self.camera.config.get("fps"),
            "format": self.camera.config.get("format", "RGB888"),
            "quality": self.camera.config.get("quality", 85),
            "start_open": self.config.get("start_open", False),
            "serve_mjpeg": self.config.get("serve_mjpeg", False),
            "mjpeg_host": self.config.get("mjpeg_host", "0.0.0.0"),
            "mjpeg_port": self.config.get("mjpeg_port", 5000)
        }
        
        self.bus.emit(message.response(settings))
        LOG.debug(f"Camera settings sent: {settings}")

    def handle_set_settings(self, message: Message) -> None:
        """
        Handle request to update camera settings.
        
        Expected data: {"width": 1920, "height": 1080, "fps": 30, ...}
        Response: ovos.phal.camera.settings.set.response
        """
        if not self.validate_message_context(message):
            return
        
        new_settings = message.data
        success = self.camera.update_settings(new_settings)
        
        response = {
            "success": success,
            "applied_settings": new_settings if success else {},
            "error": None if success else "Failed to apply settings"
        }
        
        self.bus.emit(message.response(response))
        LOG.info(f"Camera settings update: {response}")

    def handle_restart(self, message: Message) -> None:
        """
        Handle request to restart the camera.
        
        Response: ovos.phal.camera.restart.response
        """
        if not self.validate_message_context(message):
            return
        
        # Stop AI monitoring if active
        was_monitoring = self.ai_monitoring_active
        if was_monitoring:
            self._stop_ai_monitoring()
        
        success = self.camera.restart()
        
        # Restart AI monitoring if it was active
        if was_monitoring and success and self.camera.ai_model_info.get("inference_enabled"):
            self._start_ai_monitoring()
        
        response = {
            "success": success,
            "message": "Camera restarted successfully" if success else "Camera restart failed"
        }
        
        self.bus.emit(message.response(response))
        LOG.info(f"Camera restart result: {response}")

    def handle_reset(self, message: Message) -> None:
        """
        Handle request to reset the camera to default settings.
        
        Response: ovos.phal.camera.reset.response
        """
        if not self.validate_message_context(message):
            return
        
        # Stop AI monitoring if active
        if self.ai_monitoring_active:
            self._stop_ai_monitoring()
        
        result = self.camera.reset()
        
        self.bus.emit(message.response(result))
        LOG.info(f"Camera reset result: {result}")

    def handle_ai_load_model(self, message: Message) -> None:
        """
        Handle request to load an AI model on IMX500.
        
        Expected data: {"model_path": "/path/to/model.rpk", "model_name": "Optional Name"}
        Response: ovos.phal.camera.ai.model.load.response
        """
        if not self.validate_message_context(message):
            return
        
        model_path = message.data.get("model_path")
        model_name = message.data.get("model_name", "")
        
        if not model_path:
            self.bus.emit(message.response({"success": False, "error": "model_path required"}))
            return
        
        result = self.camera.load_ai_model(model_path, model_name)
        self.bus.emit(message.response(result))
        LOG.info(f"AI model load result: {result}")

    def handle_ai_set_inference(self, message: Message) -> None:
        """
        Handle request to enable/disable AI inference.
        
        Expected data: {"enabled": true/false}
        Response: ovos.phal.camera.ai.inference.set.response
        """
        if not self.validate_message_context(message):
            return
        
        enabled = message.data.get("enabled", False)
        result = self.camera.set_ai_inference(enabled)
        
        # Start/stop monitoring thread for continuous inference
        if enabled and result.get("success"):
            self._start_ai_monitoring()
        elif not enabled:
            self._stop_ai_monitoring()
        
        self.bus.emit(message.response(result))
        LOG.info(f"AI inference set result: {result}")

    def handle_ai_get_inference(self, message: Message) -> None:
        """
        Handle request to get latest AI inference results.
        
        Response: ovos.phal.camera.ai.inference.response
        """
        if not self.validate_message_context(message):
            return
        
        results = self.camera.get_ai_inference()
        
        if results is None:
            self.bus.emit(message.response({
                "success": False,
                "error": "AI inference not available or not enabled"
            }))
        else:
            self.bus.emit(message.response({
                "success": True,
                "results": results
            }))
        
        LOG.debug(f"AI inference results sent")

    def _start_ai_monitoring(self) -> None:
        """Start background thread to monitor AI inference and emit results."""
        if self.ai_monitoring_active:
            return
        
        self.ai_monitoring_active = True
        
        def monitor_loop():
            import time
            while self.ai_monitoring_active:
                try:
                    results = self.camera.get_ai_inference()
                    if results:
                        # Emit inference results to bus
                        self.bus.emit(Message(
                            "ovos.phal.camera.ai.inference.event",
                            data=results
                        ))
                    time.sleep(0.1)  # 10 FPS inference rate
                except Exception as e:
                    LOG.error(f"AI monitoring error: {e}")
                    time.sleep(1)
        
        self.ai_monitoring_thread = Thread(target=monitor_loop, daemon=True)
        self.ai_monitoring_thread.start()
        LOG.info("AI monitoring thread started")

    def _stop_ai_monitoring(self) -> None:
        """Stop the AI inference monitoring thread."""
        self.ai_monitoring_active = False
        if self.ai_monitoring_thread:
            self.ai_monitoring_thread = None
        LOG.info("AI monitoring thread stopped")

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
        self._stop_ai_monitoring()
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

