"""
System Test Script for Forge Registry Station
Tests all components individually before full operation
"""

import cv2
import numpy as np
import socket
import time

print("=" * 70)
print("FORGE REGISTRY STATION - SYSTEM TEST")
print("=" * 70)

# ============================================================================
# TEST 1: Camera Detection
# ============================================================================

print("\n[TEST 1] Camera Detection")
print("-" * 70)

try:
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            height, width = frame.shape[:2]
            print(f"✓ Camera 0 detected: {width}x{height}")
            cap.release()
        else:
            print("✗ Camera opened but cannot read frames")
    else:
        print("✗ Cannot open camera 0")
        print("  Try changing CAMERA_INDEX to 1 or 2")
except Exception as e:
    print(f"✗ Camera error: {e}")

# ============================================================================
# TEST 2: Aruco Dictionary
# ============================================================================

print("\n[TEST 2] Aruco Dictionary")
print("-" * 70)

try:
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    print(f"✓ Aruco dictionary loaded: DICT_4X4_50")
    print(f"  Dictionary contains {aruco_dict.markerSize} markers")
    
    # Generate a test marker
    test_marker = cv2.aruco.generateImageMarker(aruco_dict, 1, 200)
    cv2.imwrite("test_marker_id1.png", test_marker)
    print(f"✓ Test marker generated: test_marker_id1.png")
    
except Exception as e:
    print(f"✗ Aruco error: {e}")
    print("  Make sure opencv-contrib-python is installed")
    print("  Run: pip install opencv-contrib-python")

# ============================================================================
# TEST 3: UDP Socket
# ============================================================================

print("\n[TEST 3] UDP Socket")
print("-" * 70)

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 5001))
    sock.settimeout(0.1)
    print(f"✓ UDP socket created and bound to port 5001")
    sock.close()
except Exception as e:
    print(f"✗ Socket error: {e}")

# ============================================================================
# TEST 4: Network Connectivity
# ============================================================================

print("\n[TEST 4] Network Connectivity")
print("-" * 70)

pico_ip = input("Enter Pico W IP address (or press Enter to skip): ").strip()

if pico_ip:
    try:
        import subprocess
        result = subprocess.run(['ping', '-n', '1', pico_ip], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            print(f"✓ Pico W reachable at {pico_ip}")
        else:
            print(f"✗ Cannot reach {pico_ip}")
            print("  Check WiFi connection and IP address")
    except Exception as e:
        print(f"✗ Ping error: {e}")
else:
    print("  Skipped - no IP provided")

# ============================================================================
# TEST 5: Full Camera + Aruco Detection
# ============================================================================

print("\n[TEST 5] Full Camera + Aruco Detection")
print("-" * 70)
print("Opening camera for 10 seconds...")
print("Hold an Aruco marker in front of the camera")
print("Press 'q' to quit early")

try:
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
    
    start_time = time.time()
    detected_ids = set()
    frame_count = 0
    
    while time.time() - start_time < 10:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Detect markers
        corners, ids, rejected = detector.detectMarkers(frame)
        
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            for marker_id in ids:
                detected_ids.add(int(marker_id[0]))
        
        # Draw instructions
        cv2.putText(frame, "Hold Aruco marker in view", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Detected IDs: {sorted(detected_ids)}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.putText(frame, "Press 'q' to quit", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow('Aruco Detection Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\nTest Results:")
    print(f"  Frames processed: {frame_count}")
    print(f"  Markers detected: {sorted(detected_ids) if detected_ids else 'None'}")
    
    if detected_ids:
        print(f"✓ Aruco detection working!")
        if 1 in detected_ids or 2 in detected_ids:
            print(f"✓ Markers ID 1 or 2 detected (ready for forge registry)")
    else:
        print(f"✗ No markers detected")
        print("  Troubleshooting:")
        print("  - Generate markers with: python generate_aruco.py")
        print("  - Ensure good lighting")
        print("  - Hold marker flat and steady")
        print("  - Try different distances from camera")
    
except Exception as e:
    print(f"✗ Detection test error: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("\nIf all tests passed:")
print("  1. Flash EmbeddedMS3.uf2 to Pico W")
print("  2. Note Pico W IP from serial monitor")
print("  3. Update PICO_IP in aruco_wifi_tracker.py")
print("  4. Run: python aruco_wifi_tracker.py")
print("\nIf tests failed:")
print("  - Check error messages above")
print("  - Verify opencv-contrib-python installed")
print("  - Test camera with other applications")
print("  - Check network connectivity")
print("\nFor full setup guide, see: FORGE_REGISTRY_SETUP.md")
print("=" * 70)
