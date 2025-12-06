"""
HSV Color Range Calibration Tool
Interactive tool to find optimal HSV color ranges for object detection
Author: GitHub Copilot
Date: November 2025

Usage:
1. Run this script with your webcam active
2. Place your colored object in view
3. Adjust the trackbars to isolate your object (white on black mask)
4. Press 's' to save the values to a file
5. Use the printed HSV ranges in your main tracking script
"""

import cv2
import numpy as np

# Global variables for trackbar values
h_min = 0
h_max = 179
s_min = 0
s_max = 255
v_min = 0
v_max = 255

def nothing(x):
    """Dummy callback function for trackbars"""
    pass

def create_trackbars():
    """Create trackbar window with HSV range controls"""
    cv2.namedWindow('HSV Trackbars')
    
    # Hue range: 0-179 in OpenCV
    cv2.createTrackbar('H Min', 'HSV Trackbars', 0, 179, nothing)
    cv2.createTrackbar('H Max', 'HSV Trackbars', 179, 179, nothing)
    
    # Saturation range: 0-255
    cv2.createTrackbar('S Min', 'HSV Trackbars', 0, 255, nothing)
    cv2.createTrackbar('S Max', 'HSV Trackbars', 255, 255, nothing)
    
    # Value range: 0-255
    cv2.createTrackbar('V Min', 'HSV Trackbars', 0, 255, nothing)
    cv2.createTrackbar('V Max', 'HSV Trackbars', 255, 255, nothing)

def get_trackbar_values():
    """Read current trackbar values"""
    h_min = cv2.getTrackbarPos('H Min', 'HSV Trackbars')
    h_max = cv2.getTrackbarPos('H Max', 'HSV Trackbars')
    s_min = cv2.getTrackbarPos('S Min', 'HSV Trackbars')
    s_max = cv2.getTrackbarPos('S Max', 'HSV Trackbars')
    v_min = cv2.getTrackbarPos('V Min', 'HSV Trackbars')
    v_max = cv2.getTrackbarPos('V Max', 'HSV Trackbars')
    
    return h_min, h_max, s_min, s_max, v_min, v_max

def save_hsv_values(h_min, h_max, s_min, s_max, v_min, v_max):
    """Save HSV values to a text file"""
    with open('hsv_values.txt', 'w') as f:
        f.write("HSV Color Range Configuration\n")
        f.write("=" * 50 + "\n\n")
        f.write("Copy these values to your tracking script:\n\n")
        f.write(f"LOWER_HSV = np.array([{h_min}, {s_min}, {v_min}])\n")
        f.write(f"UPPER_HSV = np.array([{h_max}, {s_max}, {v_max}])\n\n")
        f.write("Individual values:\n")
        f.write(f"H Min: {h_min}\n")
        f.write(f"H Max: {h_max}\n")
        f.write(f"S Min: {s_min}\n")
        f.write(f"S Max: {s_max}\n")
        f.write(f"V Min: {v_min}\n")
        f.write(f"V Max: {v_max}\n")
    
    print("\nHSV values saved to 'hsv_values.txt'")
    print(f"LOWER_HSV = np.array([{h_min}, {s_min}, {v_min}])")
    print(f"UPPER_HSV = np.array([{h_max}, {s_max}, {v_max}])")

def main():
    """Main calibration function"""
    print("=" * 60)
    print("HSV COLOR RANGE CALIBRATION TOOL")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Place your colored object in the camera view")
    print("2. Adjust the trackbars to isolate the object (white on mask)")
    print("3. The object should appear WHITE in the 'Mask' window")
    print("4. Everything else should be BLACK")
    print("\nControls:")
    print("  's' - Save HSV values to file")
    print("  'q' - Quit application")
    print("=" * 60)
    
    # Initialize camera (use same index as main tracking script)
    CAMERA_INDEX = 1  # Match the camera index from OpenCV.py
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print("ERROR: Cannot access camera!")
        return
    
    # Create trackbar window
    create_trackbars()
    
    print("\nCamera initialized. Adjust trackbars to calibrate...")
    
    # Preset values for common colors (can be loaded with keyboard shortcuts)
    presets = {
        'r': {'name': 'Red', 'lower': [0, 120, 70], 'upper': [10, 255, 255]},
        'g': {'name': 'Green', 'lower': [40, 40, 40], 'upper': [80, 255, 255]},
        'b': {'name': 'Blue', 'lower': [100, 100, 100], 'upper': [130, 255, 255]},
        'y': {'name': 'Yellow', 'lower': [20, 100, 100], 'upper': [30, 255, 255]},
        'o': {'name': 'Orange', 'lower': [10, 100, 100], 'upper': [20, 255, 255]},
    }
    
    while True:
        # Capture frame
        ret, frame = cap.read()
        
        if not ret:
            print("ERROR: Failed to capture frame!")
            break
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Get current trackbar values
        h_min, h_max, s_min, s_max, v_min, v_max = get_trackbar_values()
        
        # Create mask
        lower_bound = np.array([h_min, s_min, v_min])
        upper_bound = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        # Apply morphological operations to clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask_cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_CLOSE, kernel)
        
        # Apply mask to original frame
        result = cv2.bitwise_and(frame, frame, mask=mask_cleaned)
        
        # Display current HSV values on frame
        cv2.putText(frame, f"H: {h_min}-{h_max}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"S: {s_min}-{s_max}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"V: {v_min}-{v_max}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Display instructions
        cv2.putText(frame, "Press 's' to save", (10, frame.shape[0] - 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, "Press 'q' to quit", (10, frame.shape[0] - 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show windows
        cv2.imshow('Original', frame)
        cv2.imshow('Mask', mask_cleaned)
        cv2.imshow('Result', result)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\nClosing calibration tool...")
            break
        elif key == ord('s'):
            save_hsv_values(h_min, h_max, s_min, s_max, v_min, v_max)
        elif key in [ord(k) for k in presets.keys()]:
            # Load preset
            preset_key = chr(key)
            preset = presets[preset_key]
            print(f"\nLoaded {preset['name']} preset")
            cv2.setTrackbarPos('H Min', 'HSV Trackbars', preset['lower'][0])
            cv2.setTrackbarPos('H Max', 'HSV Trackbars', preset['upper'][0])
            cv2.setTrackbarPos('S Min', 'HSV Trackbars', preset['lower'][1])
            cv2.setTrackbarPos('S Max', 'HSV Trackbars', preset['upper'][1])
            cv2.setTrackbarPos('V Min', 'HSV Trackbars', preset['lower'][2])
            cv2.setTrackbarPos('V Max', 'HSV Trackbars', preset['upper'][2])
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Calibration tool closed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
