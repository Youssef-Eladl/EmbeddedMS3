"""Quick script to list all available cameras"""
import cv2

print("Scanning for cameras...")
print("-" * 60)

for i in range(10):  # Check indices 0-9
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            # Try to get camera name (works on some systems)
            backend = cap.getBackendName()
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"Camera {i}: FOUND - {width}x{height} - Backend: {backend}")
        else:
            print(f"Camera {i}: Found but couldn't read frame")
        cap.release()
    else:
        pass  # Not available

print("-" * 60)
print("\nTry each index in OpenCV.py by changing CAMERA_INDEX")
