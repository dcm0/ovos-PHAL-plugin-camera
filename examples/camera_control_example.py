#!/usr/bin/env python3
"""
Example script demonstrating OVOS Camera PHAL Plugin bus control.

This script shows how to interact with the camera plugin via the message bus
to build control panels, wizards, or automation.

Usage:
    python camera_control_example.py
"""

from ovos_bus_client import Message, MessageBusClient
import time
import sys


def example_1_camera_detection():
    """Example 1: Detect and query camera information."""
    print("\n" + "="*60)
    print("Example 1: Camera Detection")
    print("="*60)
    
    bus = MessageBusClient()
    bus.run_in_thread()
    
    # Check if camera is available
    print("\n1. Checking camera availability...")
    
    def handle_pong(message):
        print("   ✓ Camera plugin is responding!")
    
    bus.once('ovos.phal.camera.pong', handle_pong)
    bus.emit(Message('ovos.phal.camera.ping'))
    time.sleep(0.5)
    
    # Get camera info
    print("\n2. Getting camera information...")
    
    def handle_info(message):
        data = message.data
        print(f"   Camera Model: {data.get('camera_model', 'Unknown')}")
        print(f"   Camera Type: {data.get('camera_type', 'Unknown')}")
        print(f"   AI Capable: {data.get('is_ai_camera', False)}")
        print(f"   Currently Open: {data.get('is_open', False)}")
        
        if data.get('mjpeg_enabled'):
            print(f"   MJPEG Stream: {data.get('mjpeg_url')}")
        else:
            print("   MJPEG Stream: Disabled")
    
    bus.once('ovos.phal.camera.info.response', handle_info)
    bus.emit(Message('ovos.phal.camera.info.get'))
    time.sleep(1)
    
    # Get capabilities
    print("\n3. Getting camera capabilities...")
    
    def handle_caps(message):
        caps = message.data
        print(f"   Available modes: {len(caps.get('available_modes', []))}")
        
        for mode in caps.get('available_modes', [])[:3]:  # Show first 3
            size = mode.get('size', [0, 0])
            fps = mode.get('fps', 0)
            print(f"     - {size[0]}x{size[1]} @ {fps}fps")
    
    bus.once('ovos.phal.camera.capabilities.response', handle_caps)
    bus.emit(Message('ovos.phal.camera.capabilities.get'))
    time.sleep(1)
    
    bus.close()


def example_2_settings_control():
    """Example 2: Get and update camera settings."""
    print("\n" + "="*60)
    print("Example 2: Settings Control")
    print("="*60)
    
    bus = MessageBusClient()
    bus.run_in_thread()
    
    # Get current settings
    print("\n1. Current camera settings:")
    
    def handle_get_settings(message):
        settings = message.data
        print(f"   Resolution: {settings.get('width')}x{settings.get('height')}")
        print(f"   FPS: {settings.get('fps')}")
        print(f"   Quality: {settings.get('quality')}%")
        print(f"   MJPEG Enabled: {settings.get('serve_mjpeg')}")
        print(f"   MJPEG Port: {settings.get('mjpeg_port')}")
    
    bus.once('ovos.phal.camera.settings.response', handle_get_settings)
    bus.emit(Message('ovos.phal.camera.settings.get'))
    time.sleep(1)
    
    # Update settings
    print("\n2. Updating camera settings to 720p...")
    
    def handle_set_settings(message):
        if message.data.get('success'):
            print("   ✓ Settings updated successfully!")
            applied = message.data.get('applied_settings', {})
            print(f"   New resolution: {applied.get('width')}x{applied.get('height')}")
        else:
            print(f"   ✗ Failed: {message.data.get('error')}")
    
    bus.once('ovos.phal.camera.settings.set.response', handle_set_settings)
    bus.emit(Message('ovos.phal.camera.settings.set', {
        "width": 1280,
        "height": 720,
        "fps": 30,
        "quality": 90
    }))
    time.sleep(2)
    
    bus.close()


def example_3_image_capture():
    """Example 3: Capture and save images."""
    print("\n" + "="*60)
    print("Example 3: Image Capture")
    print("="*60)
    
    bus = MessageBusClient()
    bus.run_in_thread()
    
    # Capture to file
    print("\n1. Capturing image to file...")
    
    def handle_capture(message):
        if 'path' in message.data:
            print(f"   ✓ Image saved to: {message.data['path']}")
        elif 'error' in message.data:
            print(f"   ✗ Error: {message.data['error']}")
    
    bus.once('ovos.phal.camera.get.response', handle_capture)
    bus.emit(Message('ovos.phal.camera.get', {
        "path": "/tmp/camera_test.jpg"
    }))
    time.sleep(2)
    
    # Capture as base64
    print("\n2. Capturing image as base64...")
    
    def handle_capture_b64(message):
        if 'b64_frame' in message.data:
            b64_len = len(message.data['b64_frame'])
            print(f"   ✓ Got base64 image ({b64_len} characters)")
            print(f"   First 50 chars: {message.data['b64_frame'][:50]}...")
        elif 'error' in message.data:
            print(f"   ✗ Error: {message.data['error']}")
    
    bus.once('ovos.phal.camera.get.response', handle_capture_b64)
    bus.emit(Message('ovos.phal.camera.get'))
    time.sleep(2)
    
    bus.close()


def example_4_ai_camera():
    """Example 4: AI camera model loading and inference."""
    print("\n" + "="*60)
    print("Example 4: AI Camera (IMX500)")
    print("="*60)
    
    bus = MessageBusClient()
    bus.run_in_thread()
    
    # Check if AI camera
    print("\n1. Checking for AI camera...")
    
    is_ai = [False]  # Using list to modify in closure
    
    def check_ai(message):
        if message.data.get('is_ai_camera'):
            print("   ✓ AI camera detected!")
            is_ai[0] = True
        else:
            print("   ✗ Not an AI camera (skipping AI examples)")
    
    bus.once('ovos.phal.camera.info.response', check_ai)
    bus.emit(Message('ovos.phal.camera.info.get'))
    time.sleep(1)
    
    if not is_ai[0]:
        bus.close()
        return
    
    # Load AI model
    print("\n2. Loading AI model...")
    print("   (This is a simulation - provide real model path)")
    
    def handle_model_load(message):
        if message.data.get('success'):
            print("   ✓ AI model loaded successfully!")
            info = message.data.get('model_info', {})
            print(f"   Model: {info.get('model_name')}")
        else:
            print(f"   ✗ Failed: {message.data.get('error')}")
    
    bus.once('ovos.phal.camera.ai.model.load.response', handle_model_load)
    bus.emit(Message('ovos.phal.camera.ai.model.load', {
        "model_path": "/path/to/model.rpk",
        "model_name": "Object Detection v1"
    }))
    time.sleep(1)
    
    # Enable inference
    print("\n3. Enabling AI inference...")
    
    def handle_inference_set(message):
        if message.data.get('success'):
            print("   ✓ Inference enabled!")
            print("   Listening for detection events...")
        else:
            print(f"   ✗ Failed: {message.data.get('error')}")
    
    # Listen for inference events
    detection_count = [0]
    
    def handle_detection(message):
        detection_count[0] += 1
        detections = message.data.get('detections', [])
        if detections:
            print(f"\n   Detection #{detection_count[0]}:")
            for det in detections:
                print(f"     - {det['class']}: {det['confidence']:.2f}")
    
    bus.on('ovos.phal.camera.ai.inference.event', handle_detection)
    
    bus.once('ovos.phal.camera.ai.inference.set.response', handle_inference_set)
    bus.emit(Message('ovos.phal.camera.ai.inference.set', {"enabled": True}))
    
    # Monitor for 5 seconds
    print("\n4. Monitoring detections for 5 seconds...")
    time.sleep(5)
    
    # Disable inference
    print("\n5. Disabling inference...")
    bus.emit(Message('ovos.phal.camera.ai.inference.set', {"enabled": False}))
    time.sleep(1)
    
    bus.close()


def example_5_error_recovery():
    """Example 5: Camera error recovery and reset."""
    print("\n" + "="*60)
    print("Example 5: Error Recovery")
    print("="*60)
    
    bus = MessageBusClient()
    bus.run_in_thread()
    
    # Simulate error recovery workflow
    print("\n1. Testing camera restart...")
    
    def handle_restart(message):
        if message.data.get('success'):
            print("   ✓ Camera restarted successfully")
            print(f"   Message: {message.data.get('message')}")
        else:
            print(f"   ✗ Restart failed: {message.data.get('message')}")
    
    bus.once('ovos.phal.camera.restart.response', handle_restart)
    bus.emit(Message('ovos.phal.camera.restart'))
    time.sleep(2)
    
    # Test reset
    print("\n2. Testing camera reset to defaults...")
    
    def handle_reset(message):
        if message.data.get('success'):
            print("   ✓ Camera reset successfully")
            print(f"   Message: {message.data.get('message')}")
            print("   All custom settings cleared")
        else:
            print(f"   ✗ Reset failed: {message.data.get('error')}")
    
    bus.once('ovos.phal.camera.reset.response', handle_reset)
    bus.emit(Message('ovos.phal.camera.reset'))
    time.sleep(2)
    
    # Verify camera is working after reset
    print("\n3. Verifying camera works after reset...")
    
    def handle_verify(message):
        print(f"   Camera model: {message.data.get('camera_model')}")
        print(f"   Camera open: {message.data.get('is_open')}")
        print("   ✓ Camera operational after reset")
    
    bus.once('ovos.phal.camera.info.response', handle_verify)
    bus.emit(Message('ovos.phal.camera.info.get'))
    time.sleep(1)
    
    bus.close()


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("OVOS Camera PHAL Plugin - Control Examples")
    print("="*60)
    print("\nThese examples demonstrate how to interact with the camera")
    print("plugin via the OVOS message bus.")
    print("\nNote: The camera plugin must be running for these to work.")
    print("\nExamples include:")
    print("  1. Camera detection and information")
    print("  2. Settings control")
    print("  3. Image capture")
    print("  4. AI camera features (if available)")
    print("  5. Error recovery and reset")
    
    try:
        # Run examples
        example_1_camera_detection()
        time.sleep(1)
        
        example_2_settings_control()
        time.sleep(1)
        
        example_3_image_capture()
        time.sleep(1)
        
        example_4_ai_camera()
        time.sleep(1)
        
        example_5_error_recovery()
        
        print("\n" + "="*60)
        print("All examples completed!")
        print("="*60)
        print("\nFor more information, see CAMERAPROTOCOL.md")
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError running examples: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
