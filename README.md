# Camera Plugin for OVOS PHAL

This plugin allows users to interact with cameras using OpenCV or libcamera, take snapshots, and serve video streams over HTTP. It also provides comprehensive message bus integration for camera control, settings management, and AI camera support (IMX500).

## Features

- **Camera Detection**: Automatically detect and use compatible camera systems (libcamera on Raspberry Pi or OpenCV on other systems)
- **Dynamic Control**: Open and close the camera dynamically via bus messages
- **Error Recovery**: Restart or reset camera to recover from errors or hung states
- **Image Capture**: Capture frames and save them to a file or return as base64-encoded strings
- **MJPEG Streaming**: Serve video streams as an MJPEG feed over HTTP
- **Settings Management**: Configure resolution, FPS, quality, and more at runtime
- **AI Camera Support**: Full support for Raspberry Pi AI Camera (IMX500)
  - Load and manage AI models (.rpk format)
  - Enable/disable on-sensor inference
  - Real-time inference event streaming
  - Object detection, classification, pose estimation, and more
- **Comprehensive Bus API**: Control all features via OVOS message bus

---

## Quick Links

- **[Complete Bus Protocol Documentation](CAMERAPROTOCOL.md)** - Comprehensive API reference for building control panels and integrations
- **[Example Scripts](examples/)** - Ready-to-use examples for camera control, settings, and AI features
- **[HiveMind Integration](#hivemind-support)** - Use with HiveMind satellites

---

## HiveMind Support

This plugin can be used both in OVOS and with [HiveMind](https://github.com/JarbasHiveMind) satellites.

Be sure to allow `"ovos.phal.camera.pong"` in your hivemind for your satellite to be able to report camera support

```bash
hivemind-core allow-msg "ovos.phal.camera.pong"
```

---

## Installation

1. Install required dependencies:

   ```bash
   pip install ovos-phal-plugin-camera
   ```

2. Add the plugin to your OVOS PHAL configuration:

   ```json
   {
       "PHAL": {
           "ovos-phal-plugin-camera": {
               "video_source": 0,
               "start_open": false,
               "serve_mjpeg": false,
               "mjpeg_host": "0.0.0.0",
               "mjpeg_port": 5000
           }
       }
   }
   ```

### Additional Steps for Raspberry Pi Users

If you plan to use this skill on a Raspberry Pi, it requires access to the `libcamera` package for the Picamera2 library to function correctly. Due to how `libcamera` is installed on the Raspberry Pi (system-wide), additional steps are necessary to ensure compatibility when using a Python virtual environment (venv).

In these examples we use the default .venv location from ovos-installer, `~/.venvs/ovos`, adjust as needed

#### **Steps to Enable `libcamera` in Your Virtual Environment**

1. **Install Required System Packages**  
   Before proceeding, ensure that `libcamera` and its dependencies are installed on your Raspberry Pi. Run the following commands:  
   ```bash
   sudo apt install -y python3-libcamera python3-kms++ libcap-dev
   ```

2. **Modify the Virtual Environment Configuration**  
   If you already have a virtual environment set up, enable access to system-wide packages by modifying the `pyvenv.cfg` file in the virtual environment directory:  
   ```bash
   nano ~/.venvs/ovos/pyvenv.cfg
   ```

   Add or update the following line:  
   ```plaintext
   include-system-site-packages = true
   ```

   Save the file and exit.

3. **Verify Access to `libcamera`**  
   Activate your virtual environment:  
   ```bash
   source ~/.venvs/ovos/bin/activate
   ```

   Check if the `libcamera` package is accessible:  
   ```bash
   python3 -c "import libcamera; print('libcamera is accessible')"
   ```

#### **Why Are These Steps Necessary?**
The `libcamera` package is not available on PyPI and is installed system-wide on the Raspberry Pi. Virtual environments typically isolate themselves from system-wide Python packages, so these adjustments allow the skill to access `libcamera` while still benefiting from the isolation provided by a venv.

#### **Notes**
- These steps are specific to Raspberry Pi users who want to utilize the Picamera2 library for camera functionality. On other platforms, the skill defaults to using OpenCV, which does not require additional configuration.
- Ensure that `libcamera` is installed on your Raspberry Pi before attempting these steps. You can test this by running:  
  ```bash
  libcamera-still --version
  ```
  
---

## Configuration Options

| Option         | Type   | Default   | Description                                           |
| -------------- | ------ | --------- | ----------------------------------------------------- |
| `video_source` | `int`  | `0`       | Index of the video source to use for the camera       |
| `width`        | `int`  | `null`    | Camera capture width in pixels (auto if not set)      |
| `height`       | `int`  | `null`    | Camera capture height in pixels (auto if not set)     |
| `fps`          | `int`  | `null`    | Frames per second (auto if not set)                   |
| `format`       | `str`  | `RGB888`  | Pixel format for libcamera                            |
| `quality`      | `int`  | `85`      | JPEG compression quality (1-100)                      |
| `start_open`   | `bool` | `false`   | Whether to open the camera at plugin startup          |
| `serve_mjpeg`  | `bool` | `false`   | Whether to start an MJPEG server for video streaming  |
| `mjpeg_host`   | `str`  | `0.0.0.0` | Host address for MJPEG server                         |
| `mjpeg_port`   | `int`  | `5000`    | Port for the MJPEG server                             |

---

## Bus Events

### Core Events

| Event Name               | Description                       | Payload                     |
| ------------------------ | --------------------------------- | --------------------------- |
| `ovos.phal.camera.ping`  | Check if camera is available      | None                        |
| `ovos.phal.camera.open`  | Opens the camera                  | None                        |
| `ovos.phal.camera.close` | Closes the camera                 | None                        |
| `ovos.phal.camera.get`   | Captures a frame from the camera  | `{ "path": "<file_path>" }` |

### Information & Capabilities

| Event Name                            | Description                          | Payload |
| ------------------------------------- | ------------------------------------ | ------- |
| `ovos.phal.camera.info.get`           | Get camera model and info            | None    |
| `ovos.phal.camera.capabilities.get`   | Get available modes and capabilities | None    |
| `ovos.phal.camera.settings.get`       | Get current settings                 | None    |

### Settings Control

| Event Name                      | Description              | Payload                                              |
| ------------------------------- | ------------------------ | ---------------------------------------------------- |
| `ovos.phal.camera.settings.set` | Update camera settings   | `{ "width": 1920, "height": 1080, "fps": 30, ... }` |

### AI Camera (IMX500)

| Event Name                              | Description                     | Payload                                               |
| --------------------------------------- | ------------------------------- | ----------------------------------------------------- |
| `ovos.phal.camera.ai.model.load`        | Load AI model on IMX500         | `{ "model_path": "/path/to/model.rpk", ... }`        |
| `ovos.phal.camera.ai.inference.set`     | Enable/disable AI inference     | `{ "enabled": true }`                                 |
| `ovos.phal.camera.ai.inference.get`     | Get latest inference results    | None                                                  |

### Emitted Events

| Event Name                              | Description                      | Payload                                                           |
| --------------------------------------- | -------------------------------- | ----------------------------------------------------------------- |
| `ovos.phal.camera.pong`                 | Response to ping                 | None                                                              |
| `ovos.phal.camera.get.response`         | Response for captured frame      | `{ "path": "<file_path>" }` or `{ "b64_frame": "<base64_data>" }` |
| `ovos.phal.camera.info.response`        | Camera information               | Camera model, type, AI capabilities                               |
| `ovos.phal.camera.capabilities.response`| Available modes and settings     | Resolutions, FPS options, current config                          |
| `ovos.phal.camera.settings.response`    | Current settings                 | All configuration values                                          |
| `ovos.phal.camera.settings.set.response`| Settings update result           | Success/failure status                                            |
| `ovos.phal.camera.restart.response`     | Restart result                   | Success/failure status                                            |
| `ovos.phal.camera.reset.response`       | Reset result                     | Success/failure status                                            |
| `ovos.phal.camera.ai.inference.event`   | Continuous inference results     | Detection/classification results (auto-emitted when enabled)      |

**See [CAMERAPROTOCOL.md](CAMERAPROTOCOL.md) for complete message specifications and examples.**

---

## Usage

### Basic Camera Control

**Open the camera:**
```python
bus.emit(Message("ovos.phal.camera.open"))
```

**Close the camera:**
```python
bus.emit(Message("ovos.phal.camera.close"))
```

**Capture a frame:**
```python
# Save to file
bus.emit(Message("ovos.phal.camera.get", {"path": "/path/to/save/image.jpg"}))

# Get as base64
bus.emit(Message("ovos.phal.camera.get"))
```

**Restart camera (error recovery):**
```python
bus.emit(Message("ovos.phal.camera.restart"))
```

**Reset camera to defaults:**
```python
bus.emit(Message("ovos.phal.camera.reset"))
```

### Camera Information & Settings

**Get camera info:**
```python
def handle_info(message):
    print(f"Camera: {message.data['camera_model']}")
    print(f"AI Capable: {message.data['is_ai_camera']}")

bus.once('ovos.phal.camera.info.response', handle_info)
bus.emit(Message('ovos.phal.camera.info.get'))
```

**Update settings:**
```python
bus.emit(Message('ovos.phal.camera.settings.set', {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "quality": 90
}))
```

### AI Camera (IMX500)

**Load AI model:**
```python
bus.emit(Message('ovos.phal.camera.ai.model.load', {
    "model_path": "/home/pi/models/object_detection.rpk",
    "model_name": "Object Detection"
}))
```

**Enable inference and monitor detections:**
```python
def handle_detections(message):
    for detection in message.data.get('detections', []):
        print(f"Detected: {detection['class']} ({detection['confidence']:.2f})")

bus.on('ovos.phal.camera.ai.inference.event', handle_detections)
bus.emit(Message('ovos.phal.camera.ai.inference.set', {"enabled": True}))
```

**For complete examples, see the [examples/](examples/) directory.**

### MJPEG Server

If the `serve_mjpeg` option is enabled in the configuration, the MJPEG feed will be accessible at:

```
http://<mjpeg_host>:<mjpeg_port>/video_feed
```

You can use the MJPEG feed to integrate this camera [into Home Assistant](https://www.home-assistant.io/integrations/mjpeg/)


---

## License

This project is licensed under the [Apache 2.0 License](LICENSE).
