# OVOS Camera PHAL Plugin - Bus Protocol Documentation

This document describes all bus messages available for interacting with the OVOS Camera PHAL plugin. Use this to build control panels, wizards, or automation scripts.

## Table of Contents

- [Camera Detection & Info](#camera-detection--info)
- [Camera Control](#camera-control)
- [Settings Management](#settings-management)
- [Image Capture](#image-capture)
- [MJPEG Streaming](#mjpeg-streaming)
- [AI Camera (IMX500) Support](#ai-camera-imx500-support)
- [Complete Message Reference](#complete-message-reference)
- [Example Workflows](#example-workflows)

---

## Camera Detection & Info

### Check Camera Availability

**Message:** `ovos.phal.camera.ping`

**Request Data:** None

**Response:** `ovos.phal.camera.pong`

**Response Data:** None

**Description:** Simple ping to check if camera plugin is loaded and responding.

**Example:**
```python
from ovos_bus_client import Message, MessageBusClient

bus = MessageBusClient()
bus.run_in_thread()

def handle_pong(message):
    print("Camera is available!")

bus.once('ovos.phal.camera.pong', handle_pong)
bus.emit(Message('ovos.phal.camera.ping'))
```

### Get Camera Information

**Message:** `ovos.phal.camera.info.get`

**Request Data:** None

**Response:** `ovos.phal.camera.info.response`

**Response Data:**
```json
{
  "camera_type": "libcamera",
  "camera_model": "imx500",
  "is_ai_camera": true,
  "is_open": true,
  "mjpeg_enabled": true,
  "mjpeg_url": "http://0.0.0.0:5000/video_feed"
}
```

**Fields:**
- `camera_type`: `"libcamera"` (Raspberry Pi) or `"opencv"` (generic webcam)
- `camera_model`: Detected camera model (e.g., "imx500", "imx219", "Unknown")
- `is_ai_camera`: Boolean indicating if this is an AI-capable camera (IMX500)
- `is_open`: Boolean indicating if camera is currently open/active
- `mjpeg_enabled`: Boolean indicating if MJPEG streaming is enabled
- `mjpeg_url`: URL to access MJPEG stream (null if disabled)

### Get Camera Capabilities

**Message:** `ovos.phal.camera.capabilities.get`

**Request Data:** None

**Response:** `ovos.phal.camera.capabilities.response`

**Response Data:**
```json
{
  "camera_type": "libcamera",
  "camera_model": "imx500",
  "is_ai_camera": true,
  "is_open": true,
  "current_settings": {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "format": "RGB888"
  },
  "available_modes": [
    {
      "size": [1920, 1080],
      "fps": 30,
      "format": "RGB888"
    },
    {
      "size": [1280, 720],
      "fps": 60,
      "format": "RGB888"
    }
  ],
  "ai_model_info": {
    "loaded": true,
    "model_name": "object_detection_v1",
    "model_path": "/path/to/model.rpk",
    "inference_enabled": false
  }
}
```

---

## Camera Control

### Open Camera

**Message:** `ovos.phal.camera.open`

**Request Data:** None

**Response:** None

**Description:** Opens/activates the camera if not already open.

### Close Camera

**Message:** `ovos.phal.camera.close`

**Request Data:** None

**Response:** None

**Description:** Closes/deactivates the camera.

---

## Settings Management

### Get Current Settings

**Message:** `ovos.phal.camera.settings.get`

**Request Data:** None

**Response:** `ovos.phal.camera.settings.response`

**Response Data:**
```json
{
  "video_source": 0,
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "format": "RGB888",
  "quality": 85,
  "start_open": true,
  "serve_mjpeg": true,
  "mjpeg_host": "0.0.0.0",
  "mjpeg_port": 5000
}
```

**Fields:**
- `video_source`: Camera index (for systems with multiple cameras)
- `width`: Capture width in pixels (null if using default)
- `height`: Capture height in pixels (null if using default)
- `fps`: Frames per second (null if using default)
- `format`: Pixel format (e.g., "RGB888", "YUV420")
- `quality`: JPEG compression quality (1-100)
- `start_open`: Whether camera opens on plugin startup
- `serve_mjpeg`: Whether MJPEG streaming is enabled
- `mjpeg_host`: Host address for MJPEG server
- `mjpeg_port`: Port for MJPEG server

### Update Settings

**Message:** `ovos.phal.camera.settings.set`

**Request Data:**
```json
{
  "width": 1280,
  "height": 720,
  "fps": 60,
  "quality": 90
}
```

**Response:** `ovos.phal.camera.settings.set.response`

**Response Data:**
```json
{
  "success": true,
  "applied_settings": {
    "width": 1280,
    "height": 720,
    "fps": 60,
    "quality": 90
  },
  "error": null
}
```

**Notes:**
- Only include settings you want to change
- Camera will restart with new settings if it's currently open
- For libcamera, changes may require camera reopen

### Restart Camera

**Message:** `ovos.phal.camera.restart`

**Request Data:** None

**Response:** `ovos.phal.camera.restart.response`

**Response Data:**
```json
{
  "success": true,
  "message": "Camera restarted successfully"
}
```

**Description:** Restarts the camera by closing and reopening it. Useful for recovering from errors or camera hang states. If AI inference was active, it will be restarted automatically.

**Use Cases:**
- Camera appears frozen or unresponsive
- Recovery from error state
- Apply settings that require full restart
- Clear temporary camera issues

### Reset Camera

**Message:** `ovos.phal.camera.reset`

**Request Data:** None

**Response:** `ovos.phal.camera.reset.response`

**Response Data:**
```json
{
  "success": true,
  "message": "Camera reset to defaults"
}
```

**Description:** Resets the camera to default settings and restarts it. Clears all custom configuration except the video source. For AI cameras, clears loaded models and inference state.

**Use Cases:**
- Recover from misconfiguration
- Clear all custom settings
- Return to known good state
- Troubleshooting configuration issues

**Notes:**
- Preserves only the `video_source` setting
- Clears AI model and inference state
- Stops AI monitoring if active
- Requires camera to reopen with defaults

---

## Image Capture

### Capture Image

**Message:** `ovos.phal.camera.get`

**Request Data:**
```json
{
  "path": "/home/user/pictures/snapshot.jpg"
}
```

**Response:** `ovos.phal.camera.get.response`

**Response Data (with path):**
```json
{
  "path": "/home/user/pictures/snapshot.jpg"
}
```

**Response Data (base64):**
```json
{
  "b64_frame": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Notes:**
- If `path` is provided, image is saved to disk and path is returned
- If no `path` provided, base64-encoded JPEG is returned in `b64_frame`
- Camera opens temporarily if not already open

---

## MJPEG Streaming

MJPEG streaming is configured via settings and runs as a background HTTP server.

### Enable Streaming

Update settings to enable MJPEG:

```json
{
  "serve_mjpeg": true,
  "mjpeg_host": "0.0.0.0",
  "mjpeg_port": 5000
}
```

### Access Stream

Once enabled, access the stream at:
```
http://<device_ip>:<mjpeg_port>/video_feed
```

Example: `http://10.204.0.15:5000/video_feed`

**HTML Integration:**
```html
<img src="http://10.204.0.15:5000/video_feed" alt="Camera Stream">
```

---

## AI Camera (IMX500) Support

### Load AI Model

**Message:** `ovos.phal.camera.ai.model.load`

**Request Data:**
```json
{
  "model_path": "/home/user/models/object_detection.rpk",
  "model_name": "Object Detection v1"
}
```

**Response:** `ovos.phal.camera.ai.model.load.response`

**Response Data:**
```json
{
  "success": true,
  "model_info": {
    "loaded": true,
    "model_name": "Object Detection v1",
    "model_path": "/home/user/models/object_detection.rpk",
    "inference_enabled": false
  }
}
```

**Notes:**
- Only works with IMX500 AI cameras
- Model must be in `.rpk` format (Sony IMX500 model package)
- Model is loaded but inference is not started automatically

### Enable/Disable AI Inference

**Message:** `ovos.phal.camera.ai.inference.set`

**Request Data:**
```json
{
  "enabled": true
}
```

**Response:** `ovos.phal.camera.ai.inference.set.response`

**Response Data:**
```json
{
  "success": true,
  "inference_enabled": true
}
```

**Notes:**
- Starts continuous inference when enabled
- Inference results are automatically emitted to bus as events
- Stops inference monitoring thread when disabled

### Get AI Inference Results (On-Demand)

**Message:** `ovos.phal.camera.ai.inference.get`

**Request Data:** None

**Response:** `ovos.phal.camera.ai.inference.response`

**Response Data:**
```json
{
  "success": true,
  "results": {
    "timestamp": "2025-11-14T16:30:45.123Z",
    "detections": [
      {
        "class": "person",
        "confidence": 0.95,
        "bbox": [100, 150, 300, 450],
        "id": 0
      },
      {
        "class": "dog",
        "confidence": 0.87,
        "bbox": [400, 200, 600, 400],
        "id": 1
      }
    ],
    "metadata": {
      "model_name": "Object Detection v1",
      "inference_time_ms": 25
    }
  }
}
```

### AI Inference Events (Continuous)

When inference is enabled, results are automatically emitted:

**Event Message:** `ovos.phal.camera.ai.inference.event`

**Event Data:**
```json
{
  "timestamp": "2025-11-14T16:30:45.123Z",
  "detections": [
    {
      "class": "person",
      "confidence": 0.95,
      "bbox": [100, 150, 300, 450],
      "id": 0
    }
  ],
  "metadata": {
    "model_name": "Object Detection v1",
    "inference_time_ms": 25
  }
}
```

**Subscribe Example:**
```python
def handle_inference(message):
    detections = message.data.get('detections', [])
    for det in detections:
        print(f"Detected: {det['class']} ({det['confidence']:.2f})")

bus.on('ovos.phal.camera.ai.inference.event', handle_inference)
```

---

## Complete Message Reference

### Request Messages (Emit These)

| Message | Purpose | Required Data |
|---------|---------|---------------|
| `ovos.phal.camera.ping` | Check availability | None |
| `ovos.phal.camera.info.get` | Get camera info | None |
| `ovos.phal.camera.capabilities.get` | Get capabilities | None |
| `ovos.phal.camera.settings.get` | Get current settings | None |
| `ovos.phal.camera.settings.set` | Update settings | Settings object |
| `ovos.phal.camera.open` | Open camera | None |
| `ovos.phal.camera.close` | Close camera | None |
| `ovos.phal.camera.restart` | Restart camera | None |
| `ovos.phal.camera.reset` | Reset to defaults | None |
| `ovos.phal.camera.get` | Capture image | Optional: path |
| `ovos.phal.camera.ai.model.load` | Load AI model | model_path, model_name |
| `ovos.phal.camera.ai.inference.set` | Enable/disable inference | enabled (bool) |
| `ovos.phal.camera.ai.inference.get` | Get inference results | None |

### Response Messages (Listen For These)

| Message | Triggered By | Data |
|---------|--------------|------|
| `ovos.phal.camera.pong` | ping | None |
| `ovos.phal.camera.info.response` | info.get | Camera info object |
| `ovos.phal.camera.capabilities.response` | capabilities.get | Capabilities object |
| `ovos.phal.camera.settings.response` | settings.get | Settings object |
| `ovos.phal.camera.settings.set.response` | settings.set | Success/error |
| `ovos.phal.camera.restart.response` | restart | Success/message |
| `ovos.phal.camera.reset.response` | reset | Success/message |
| `ovos.phal.camera.get.response` | get | Path or base64 |
| `ovos.phal.camera.ai.model.load.response` | ai.model.load | Success/model info |
| `ovos.phal.camera.ai.inference.set.response` | ai.inference.set | Success/status |
| `ovos.phal.camera.ai.inference.response` | ai.inference.get | Inference results |

### Event Messages (Automatic Emissions)

| Message | When Emitted | Data |
|---------|--------------|------|
| `ovos.phal.camera.pong` | On startup, or ping | None |
| `ovos.phal.camera.ai.inference.event` | Continuous (when enabled) | Inference results |

---

## Example Workflows

### 1. Camera Settings Control Panel

```python
from ovos_bus_client import Message, MessageBusClient
import time

bus = MessageBusClient()
bus.run_in_thread()

# Get current camera info
def show_info(message):
    data = message.data
    print(f"Camera: {data['camera_model']}")
    print(f"Type: {data['camera_type']}")
    print(f"AI Capable: {data['is_ai_camera']}")
    print(f"Stream URL: {data.get('mjpeg_url', 'Disabled')}")

bus.once('ovos.phal.camera.info.response', show_info)
bus.emit(Message('ovos.phal.camera.info.get'))

time.sleep(1)

# Get current settings
def show_settings(message):
    settings = message.data
    print(f"\nCurrent Settings:")
    print(f"  Resolution: {settings.get('width')}x{settings.get('height')}")
    print(f"  FPS: {settings.get('fps')}")
    print(f"  Quality: {settings.get('quality')}")

bus.once('ovos.phal.camera.settings.response', show_settings)
bus.emit(Message('ovos.phal.camera.settings.get'))

time.sleep(1)

# Update settings
def settings_updated(message):
    if message.data['success']:
        print("\nSettings updated successfully!")
    else:
        print(f"\nFailed: {message.data['error']}")

bus.once('ovos.phal.camera.settings.set.response', settings_updated)
bus.emit(Message('ovos.phal.camera.settings.set', {
    "width": 1280,
    "height": 720,
    "fps": 30,
    "quality": 90
}))

time.sleep(2)
```

### 2. AI Object Detection Monitoring

```python
from ovos_bus_client import Message, MessageBusClient

bus = MessageBusClient()
bus.run_in_thread()

# Load AI model
def model_loaded(message):
    if message.data['success']:
        print("Model loaded successfully!")
        # Enable inference
        bus.emit(Message('ovos.phal.camera.ai.inference.set', {"enabled": True}))
    else:
        print(f"Failed to load model: {message.data['error']}")

bus.once('ovos.phal.camera.ai.model.load.response', model_loaded)
bus.emit(Message('ovos.phal.camera.ai.model.load', {
    "model_path": "/home/user/models/object_detection.rpk",
    "model_name": "Object Detection"
}))

# Monitor continuous inference events
def handle_detection(message):
    detections = message.data.get('detections', [])
    if detections:
        print(f"Detected {len(detections)} objects:")
        for det in detections:
            print(f"  - {det['class']}: {det['confidence']:.2f}")

bus.on('ovos.phal.camera.ai.inference.event', handle_detection)

# Keep running
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # Disable inference on exit
    bus.emit(Message('ovos.phal.camera.ai.inference.set', {"enabled": False}))
    bus.close()
```

### 3. Wizard Setup Flow

```python
from ovos_bus_client import Message, MessageBusClient
import time

bus = MessageBusClient()
bus.run_in_thread()

print("Camera Setup Wizard")
print("=" * 50)

# Step 1: Detect camera
print("\n1. Detecting camera...")
def check_camera(message):
    data = message.data
    print(f"   ✓ Found: {data['camera_model']}")
    print(f"   Type: {data['camera_type']}")
    if data['is_ai_camera']:
        print("   ✓ AI capabilities detected!")
    
    # Step 2: Get available modes
    bus.emit(Message('ovos.phal.camera.capabilities.get'))

bus.once('ovos.phal.camera.info.response', check_camera)
bus.emit(Message('ovos.phal.camera.info.get'))

time.sleep(1)

# Step 3: Show available resolutions
def show_modes(message):
    modes = message.data.get('available_modes', [])
    print("\n2. Available resolutions:")
    for i, mode in enumerate(modes):
        size = mode.get('size', [])
        fps = mode.get('fps', 0)
        print(f"   {i+1}. {size[0]}x{size[1]} @ {fps}fps")
    
    # Step 4: Configure (example: select first mode)
    if modes:
        selected = modes[0]
        print(f"\n3. Configuring camera to {selected['size'][0]}x{selected['size'][1]}...")
        bus.emit(Message('ovos.phal.camera.settings.set', {
            "width": selected['size'][0],
            "height": selected['size'][1],
            "fps": selected['fps']
        }))

bus.once('ovos.phal.camera.capabilities.response', show_modes)

time.sleep(2)

# Step 5: Enable MJPEG streaming
print("\n4. Enabling MJPEG streaming...")
def streaming_enabled(message):
    if message.data['success']:
        print("   ✓ Streaming enabled")
        # Get final info
        bus.emit(Message('ovos.phal.camera.info.get'))

bus.once('ovos.phal.camera.settings.set.response', streaming_enabled)
bus.emit(Message('ovos.phal.camera.settings.set', {
    "serve_mjpeg": True,
    "mjpeg_port": 5000
}))

time.sleep(1)

# Final confirmation
def show_final(message):
    print(f"\n✓ Setup complete!")
    print(f"   Stream available at: {message.data.get('mjpeg_url')}")

bus.once('ovos.phal.camera.info.response', show_final)

time.sleep(3)
```

### 4. Capture and Save Image

```python
from ovos_bus_client import Message, MessageBusClient
import time

bus = MessageBusClient()
bus.run_in_thread()

def image_saved(message):
    if 'path' in message.data:
        print(f"Image saved to: {message.data['path']}")
    elif 'b64_frame' in message.data:
        print(f"Got base64 image ({len(message.data['b64_frame'])} chars)")
        # You can decode and use the base64 data
    elif 'error' in message.data:
        print(f"Error: {message.data['error']}")

bus.once('ovos.phal.camera.get.response', image_saved)

# Option 1: Save to file
bus.emit(Message('ovos.phal.camera.get', {
    "path": "/home/user/snapshot.jpg"
}))

# Option 2: Get base64 (uncomment to use)
# bus.emit(Message('ovos.phal.camera.get'))

time.sleep(2)
```

### 5. Error Recovery and Reset

```python
from ovos_bus_client import Message, MessageBusClient
import time

bus = MessageBusClient()
bus.run_in_thread()

print("Camera Error Recovery Workflow")
print("=" * 50)

# Step 1: Try to capture an image (might fail)
print("\n1. Attempting to capture image...")

def handle_capture_error(message):
    if 'error' in message.data:
        print(f"   ✗ Capture failed: {message.data['error']}")
        print("\n2. Attempting camera restart...")
        
        # Try restart first
        bus.emit(Message('ovos.phal.camera.restart'))

bus.once('ovos.phal.camera.get.response', handle_capture_error)
bus.emit(Message('ovos.phal.camera.get', {"path": "/tmp/test.jpg"}))

time.sleep(1)

# Step 2: Handle restart response
def handle_restart(message):
    if message.data.get('success'):
        print("   ✓ Camera restarted successfully")
        print("\n3. Retrying capture...")
        bus.emit(Message('ovos.phal.camera.get', {"path": "/tmp/test.jpg"}))
    else:
        print("   ✗ Restart failed, trying full reset...")
        
        # If restart fails, try reset
        bus.emit(Message('ovos.phal.camera.reset'))

bus.once('ovos.phal.camera.restart.response', handle_restart)

time.sleep(1)

# Step 3: Handle reset if needed
def handle_reset(message):
    if message.data.get('success'):
        print("   ✓ Camera reset to defaults")
        print("\n4. Reconfiguring with known good settings...")
        
        # Apply safe settings
        bus.emit(Message('ovos.phal.camera.settings.set', {
            "width": 1280,
            "height": 720,
            "fps": 30
        }))
    else:
        print("   ✗ Reset failed - camera may need hardware check")

bus.once('ovos.phal.camera.reset.response', handle_reset)

time.sleep(1)

# Step 4: Verify settings applied
def handle_settings_applied(message):
    if message.data.get('success'):
        print("   ✓ Settings applied")
        print("\n5. Final capture attempt...")
        bus.emit(Message('ovos.phal.camera.get', {"path": "/tmp/test_final.jpg"}))
    else:
        print(f"   ✗ Settings failed: {message.data.get('error')}")

bus.once('ovos.phal.camera.settings.set.response', handle_settings_applied)

time.sleep(1)

# Step 5: Final verification
def handle_final_capture(message):
    if 'path' in message.data:
        print(f"   ✓ Success! Image saved: {message.data['path']}")
        print("\n✓ Camera recovered and working normally")
    else:
        print("   ✗ Camera still not responding - check hardware")

bus.once('ovos.phal.camera.get.response', handle_final_capture)

time.sleep(3)
```

---

## Configuration File Example

Place in OVOS config at `/PHAL/ovos-phal-plugin-camera`:

```json
{
  "video_source": 0,
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "format": "RGB888",
  "quality": 85,
  "start_open": true,
  "serve_mjpeg": true,
  "mjpeg_host": "0.0.0.0",
  "mjpeg_port": 5000
}
```

---

## Error Handling

All response messages include error information when operations fail:

```json
{
  "success": false,
  "error": "Description of what went wrong"
}
```

Common error scenarios:
- Camera not detected or unavailable
- Invalid settings (e.g., unsupported resolution)
- AI model file not found
- Not an AI camera (for AI operations)
- Camera already in use by another process
- Camera frozen or unresponsive

### Error Recovery

**Camera appears frozen or unresponsive:**
```python
# Try restarting the camera
def handle_restart(message):
    if message.data['success']:
        print("Camera restarted successfully")
    else:
        print("Restart failed, trying reset...")
        bus.emit(Message('ovos.phal.camera.reset'))

bus.once('ovos.phal.camera.restart.response', handle_restart)
bus.emit(Message('ovos.phal.camera.restart'))
```

**Settings causing problems:**
```python
# Reset to defaults
def handle_reset(message):
    if message.data['success']:
        print("Camera reset to defaults")
        # Reconfigure with known good settings
        bus.emit(Message('ovos.phal.camera.settings.set', {
            "width": 1280,
            "height": 720
        }))

bus.once('ovos.phal.camera.reset.response', handle_reset)
bus.emit(Message('ovos.phal.camera.reset'))
```

**AI inference stopped working:**
```python
# Restart camera and re-enable inference
bus.emit(Message('ovos.phal.camera.restart'))
# Wait for restart, then re-enable
time.sleep(2)
bus.emit(Message('ovos.phal.camera.ai.inference.set', {"enabled": True}))
```

---

## IMX500 AI Model Notes

### Model Format
- IMX500 requires models in `.rpk` (RPK Package) format
- Models must be compiled for Sony IMX500 hardware
- Different model types: object detection, classification, segmentation, pose estimation

### Model Loading
- Models are loaded into the camera's on-sensor NPU
- Loading may take several seconds
- Only one model can be active at a time
- Switching models requires unloading current model first

### Inference Output Format
The format depends on the model type:

**Object Detection:**
```json
{
  "detections": [
    {
      "class": "person",
      "confidence": 0.95,
      "bbox": [x, y, width, height],
      "id": 0
    }
  ]
}
```

**Classification:**
```json
{
  "classifications": [
    {"class": "cat", "confidence": 0.92},
    {"class": "dog", "confidence": 0.05}
  ]
}
```

**Pose Estimation:**
```json
{
  "poses": [
    {
      "keypoints": [
        {"x": 100, "y": 200, "confidence": 0.9},
        ...
      ],
      "id": 0
    }
  ]
}
```

### Performance Considerations
- Inference runs on-sensor at up to 10 FPS (model-dependent)
- No CPU overhead for inference itself
- Results are available with low latency
- Continuous monitoring emits events ~10 times per second when enabled

---

## Building a Web Control Panel

### HTML/JavaScript Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Camera Control Panel</title>
</head>
<body>
    <h1>Camera Control</h1>
    
    <div id="info">
        <h2>Camera Info</h2>
        <p>Model: <span id="model">Loading...</span></p>
        <p>Type: <span id="type">Loading...</span></p>
        <p>AI Camera: <span id="ai">Loading...</span></p>
    </div>
    
    <div id="stream">
        <h2>Live Stream</h2>
        <img id="video" src="http://localhost:5000/video_feed" alt="Camera stream">
    </div>
    
    <div id="settings">
        <h2>Settings</h2>
        <label>Resolution:
            <select id="resolution">
                <option value="1920,1080">1920x1080</option>
                <option value="1280,720">1280x720</option>
                <option value="640,480">640x480</option>
            </select>
        </label>
        <button onclick="updateSettings()">Apply</button>
    </div>
    
    <div id="ai-controls" style="display:none;">
        <h2>AI Controls</h2>
        <button onclick="enableInference()">Start Detection</button>
        <button onclick="disableInference()">Stop Detection</button>
        <div id="detections"></div>
    </div>
    
    <script>
        // Connect to OVOS bus via WebSocket
        // (Requires ovos-bus-client or similar WebSocket bridge)
        
        // Pseudo-code for bus integration
        function updateSettings() {
            const res = document.getElementById('resolution').value.split(',');
            bus.emit('ovos.phal.camera.settings.set', {
                width: parseInt(res[0]),
                height: parseInt(res[1])
            });
        }
        
        function enableInference() {
            bus.emit('ovos.phal.camera.ai.inference.set', {enabled: true});
        }
        
        function disableInference() {
            bus.emit('ovos.phal.camera.ai.inference.set', {enabled: false});
        }
        
        // Listen for detections
        bus.on('ovos.phal.camera.ai.inference.event', (data) => {
            const detections = data.detections || [];
            document.getElementById('detections').innerHTML = 
                detections.map(d => `${d.class}: ${(d.confidence*100).toFixed(1)}%`).join('<br>');
        });
    </script>
</body>
</html>
```

---

## Support and Troubleshooting

### Camera Not Detected
- Check hardware connection
- Verify camera is enabled in system config
- For RPi: `libcamera-hello` test utility
- Check OVOS logs: `ovos-logs show -l phal`

### Settings Not Applying
- Some settings require camera restart
- Check if resolution is supported by your camera
- Verify camera is not in use by another process

### AI Model Won't Load
- Verify model file exists and has correct permissions
- Check model is in `.rpk` format for IMX500
- Ensure you have an AI-capable camera
- Check available storage on device

### No Inference Results
- Ensure model is loaded first
- Enable inference explicitly
- Check camera has objects in view
- Verify model type matches expected output

---

## Version History

- **v0.3.0** - Added AI camera support, comprehensive bus protocol
- **v0.2.1** - Added settings control, capabilities detection
- **v0.2.0** - Added MJPEG streaming support
- **v0.1.0** - Initial release with basic capture

---

For more information, visit: https://github.com/OpenVoiceOS/ovos-PHAL-plugin-camera
