# Camera Control Examples

This directory contains example scripts demonstrating how to interact with the OVOS Camera PHAL Plugin via the message bus.

## Prerequisites

- OVOS Camera PHAL Plugin installed and running
- OVOS message bus accessible
- `ovos-bus-client` installed

## Running Examples

### Complete Demo

Run all examples in sequence:

```bash
python camera_control_example.py
```

This will demonstrate:
1. Camera detection and information retrieval
2. Settings control (get/update)
3. Image capture (file and base64)
4. AI camera features (if available)
5. Error recovery and reset functionality

### Individual Examples

You can also run specific functions by modifying the script or importing them:

```python
from camera_control_example import example_1_camera_detection

example_1_camera_detection()
```

## Example Breakdown

### Example 1: Camera Detection
- Ping camera to check availability
- Get camera model and type information
- Query camera capabilities
- Check if AI features are available

### Example 2: Settings Control
- Retrieve current camera settings
- Update resolution, FPS, and quality
- Verify settings were applied

### Example 3: Image Capture
- Capture image and save to file
- Capture image as base64 string
- Handle capture errors

### Example 4: AI Camera (IMX500)
- Detect AI camera capabilities
- Load AI model (.rpk file)
- Enable real-time inference
- Monitor detection events
- Disable inference

### Example 5: Error Recovery
- Restart camera to recover from errors
- Reset camera to default settings
- Verify camera functionality after reset
- Handle error scenarios gracefully

## Building Your Own Integration

Use these examples as a starting point for:
- Web-based control panels
- Voice assistant integrations
- Automation scripts
- Monitoring dashboards
- AI application frontends

See `../CAMERAPROTOCOL.md` for complete API documentation.

## Troubleshooting

**"Camera plugin not responding"**
- Ensure OVOS PHAL service is running: `systemctl --user status ovos-phal`
- Check logs: `ovos-logs show -l phal`

**"Settings not applying"**
- Some settings require camera restart
- Check if values are supported by your camera hardware

**"AI features not available"**
- Verify you have an IMX500 AI camera
- Check camera detection with Example 1

## Additional Resources

- [Complete Protocol Documentation](../CAMERAPROTOCOL.md)
- [Plugin Repository](https://github.com/OpenVoiceOS/ovos-PHAL-plugin-camera)
- [OVOS Documentation](https://openvoiceos.github.io/ovos-technical-manual/)
