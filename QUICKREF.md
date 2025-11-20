# OVOS Camera Plugin - Quick Reference Card

## Installation
```bash
pip install ovos-phal-plugin-camera
```

## Configuration Location
`~/.config/mycroft/mycroft.conf` at `/PHAL/ovos-phal-plugin-camera`

## Quick Start

### Python
```python
from ovos_bus_client import Message, MessageBusClient

bus = MessageBusClient()
bus.run_in_thread()

# Get camera info
bus.once('ovos.phal.camera.info.response', lambda m: print(m.data))
bus.emit(Message('ovos.phal.camera.info.get'))

# Capture image
bus.emit(Message('ovos.phal.camera.get', {"path": "/tmp/snap.jpg"}))

# Update settings
bus.emit(Message('ovos.phal.camera.settings.set', {
    "width": 1280, "height": 720, "fps": 30
}))
```

## Common Messages

| Action | Message | Data |
|--------|---------|------|
| **Ping camera** | `ovos.phal.camera.ping` | `{}` |
| **Get info** | `ovos.phal.camera.info.get` | `{}` |
| **Get capabilities** | `ovos.phal.camera.capabilities.get` | `{}` |
| **Get settings** | `ovos.phal.camera.settings.get` | `{}` |
| **Set settings** | `ovos.phal.camera.settings.set` | `{"width": 1920, "height": 1080, ...}` |
| **Capture image** | `ovos.phal.camera.get` | `{"path": "/path/to/image.jpg"}` |
| **Open camera** | `ovos.phal.camera.open` | `{}` |
| **Close camera** | `ovos.phal.camera.close` | `{}` |
| **Restart camera** | `ovos.phal.camera.restart` | `{}` |
| **Reset camera** | `ovos.phal.camera.reset` | `{}` |

## AI Camera Messages

| Action | Message | Data |
|--------|---------|------|
| **Load model** | `ovos.phal.camera.ai.model.load` | `{"model_path": "/path/to/model.rpk", "model_name": "..."}` |
| **Enable inference** | `ovos.phal.camera.ai.inference.set` | `{"enabled": true}` |
| **Get results** | `ovos.phal.camera.ai.inference.get` | `{}` |
| **Listen to events** | Subscribe to: `ovos.phal.camera.ai.inference.event` | Auto-emitted |

## Response Messages

All request messages get a corresponding `.response` message:
- `ovos.phal.camera.info.response`
- `ovos.phal.camera.settings.set.response`
- etc.

## Configuration Options

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

## MJPEG Stream

When `serve_mjpeg: true`:
```
http://<host>:<port>/video_feed
```

Example: `http://10.204.0.15:5000/video_feed`

## Common Patterns

### Error Recovery
```python
# Restart camera on error
bus.emit(Message('ovos.phal.camera.restart'))

# Reset to defaults if restart fails
bus.emit(Message('ovos.phal.camera.reset'))
```

### Wizard Flow
```python
# 1. Detect camera
bus.emit(Message('ovos.phal.camera.info.get'))

# 2. Get available modes
bus.emit(Message('ovos.phal.camera.capabilities.get'))

# 3. Configure
bus.emit(Message('ovos.phal.camera.settings.set', {...}))

# 4. Start streaming
bus.emit(Message('ovos.phal.camera.settings.set', {"serve_mjpeg": True}))
```

### AI Detection
```python
# 1. Load model
bus.emit(Message('ovos.phal.camera.ai.model.load', {
    "model_path": "/models/detect.rpk"
}))

# 2. Subscribe to events
bus.on('ovos.phal.camera.ai.inference.event', handle_detection)

# 3. Enable inference
bus.emit(Message('ovos.phal.camera.ai.inference.set', {"enabled": True}))
```

### Settings Control Panel
```python
# Get current
bus.emit(Message('ovos.phal.camera.settings.get'))

# Update
bus.emit(Message('ovos.phal.camera.settings.set', {
    "width": 1280,
    "height": 720,
    "quality": 90
}))

# Verify
bus.once('ovos.phal.camera.settings.set.response', 
         lambda m: print("Success!" if m.data['success'] else "Failed"))
```

## Error Handling

All responses include `success` field:
```python
def handle_response(message):
    if message.data.get('success') == False:
        print(f"Error: {message.data.get('error')}")
    else:
        # Handle success
        pass
```

## Resources

- **Full Protocol**: `CAMERAPROTOCOL.md`
- **Examples**: `examples/camera_control_example.py`
- **README**: `README.md`
- **Summary**: `SUMMARY.md`

## Troubleshooting

**Camera not detected:**
```bash
# Check PHAL service
systemctl --user status ovos-phal

# Check logs
ovos-logs show -l phal | grep camera
```

**Camera frozen or unresponsive:**
```python
# Try restart
bus.emit(Message('ovos.phal.camera.restart'))

# If that fails, reset
bus.emit(Message('ovos.phal.camera.reset'))
```

**Settings not applying:**
- Check if resolution is supported
- Some settings need camera restart
- Verify values are valid for your hardware
- Try resetting to defaults first

**AI features not working:**
- Confirm IMX500 camera detected
- Check model file exists and is `.rpk` format
- Verify model is loaded before enabling inference

## Quick Test

```bash
python examples/camera_control_example.py
```

---

**Full documentation:** [CAMERAPROTOCOL.md](CAMERAPROTOCOL.md)
