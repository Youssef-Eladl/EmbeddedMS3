"""
5x5 Grid Object Tracking System
Real-time computer vision system for tracking colored objects on a physical grid
Author: GitHub Copilot
Date: November 2025
"""

import cv2
import numpy as np
import time

# ============================================================================
# CONFIGURATION SECTION - ADJUST THESE VALUES FOR YOUR SETUP
# ============================================================================

# HSV Color Range for Object Detection (adjust for your object color)
# Values optimized for metallic coin detection (gold/silver colored objects)
LOWER_HSV = np.array([0, 120, 70])     # Lower bound [Hue, Saturation, Value]
UPPER_HSV = np.array([10, 255, 255])     # Upper bound [Hue, Saturation, Value]

# Alternative range for better coin detection (can be None if not needed)
LOWER_HSV_ALT = None  # np.array([170, 120, 70])
UPPER_HSV_ALT = None  # np.array([180, 255, 255])

# Grid Configuration
GRID_SIZE = 5  # 5x5 grid
MIN_OBJECT_AREA = 50  # Minimum contour area to be considered valid (pixels²)

# Camera Configuration
CAMERA_INDEX = 1  # 0 for default webcam, 1 for external camera, 2 for Iriun Webcam
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# Display Configuration
SHOW_GRID_OVERLAY = True
SHOW_DETECTION_CIRCLE = True
SHOW_CELL_HIGHLIGHT = True
SHOW_FPS = True
SHOW_ARUCO_MARKERS = True

# ArUco Configuration
ARUCO_DICT = cv2.aruco.DICT_4X4_50  # ArUco dictionary type (can also use DICT_5X5_100, DICT_6X6_250, etc.)

# ============================================================================
# GRID DRAWING FUNCTIONS
# ============================================================================

def draw_grid_overlay(frame, grid_size=5):
    """Draw a 5x5 grid overlay on the frame"""
    height, width = frame.shape[:2]
    cell_width = width // grid_size
    cell_height = height // grid_size
    
    # Draw vertical lines
    for i in range(1, grid_size):
        x = i * cell_width
        cv2.line(frame, (x, 0), (x, height), (255, 255, 255), 2)
    
    # Draw horizontal lines
    for i in range(1, grid_size):
        y = i * cell_height
        cv2.line(frame, (0, y), (width, y), (255, 255, 255), 2)
    
    return frame

def highlight_cell(frame, row, col, grid_size=5):
    """Highlight the active cell where the object is located"""
    height, width = frame.shape[:2]
    cell_width = width // grid_size
    cell_height = height // grid_size
    
    # Calculate cell boundaries
    x1 = col * cell_width
    y1 = row * cell_height
    x2 = x1 + cell_width
    y2 = y1 + cell_height
    
    # Draw semi-transparent rectangle
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    
    # Draw cell border
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
    
    return frame

# ============================================================================
# OBJECT DETECTION FUNCTIONS
# ============================================================================

def detect_object(frame, lower_hsv, upper_hsv, lower_hsv_alt=None, upper_hsv_alt=None):
    """
    Detect colored object in frame using HSV color thresholding
    Returns: centroid coordinates (cx, cy) and contour area, or (None, None, 0)
    """
    # Convert to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Create mask for primary color range
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
    
    # Add alternative range if provided (useful for red detection)
    if lower_hsv_alt is not None and upper_hsv_alt is not None:
        mask_alt = cv2.inRange(hsv, lower_hsv_alt, upper_hsv_alt)
        mask = cv2.bitwise_or(mask, mask_alt)
    
    # Apply morphological operations to reduce noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        return None, None, 0
    
    # Find the largest contour
    largest_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_contour)
    
    # Only process if area is above minimum threshold
    if area < MIN_OBJECT_AREA:
        return None, None, 0
    
    # Calculate centroid using image moments
    M = cv2.moments(largest_contour)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return cx, cy, area
    
    return None, None, 0

# ============================================================================
# ARUCO MARKER DETECTION FUNCTIONS
# ============================================================================

def detect_aruco_markers(frame, aruco_dict_type):
    """
    Detect ArUco markers in the frame
    Returns: list of marker IDs and their corner coordinates
    """
    # Load ArUco dictionary and parameters
    aruco_dict = cv2.aruco.getPredefinedDictionary(aruco_dict_type)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
    
    # Detect markers
    corners, ids, rejected = detector.detectMarkers(frame)
    
    return corners, ids

def draw_aruco_markers(frame, corners, ids):
    """
    Draw detected ArUco markers on the frame with IDs
    """
    if ids is not None and len(ids) > 0:
        # Draw marker boundaries
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        
        # Add ID labels at marker centers
        for i, marker_id in enumerate(ids):
            # Calculate marker center
            corner = corners[i][0]
            center_x = int(np.mean(corner[:, 0]))
            center_y = int(np.mean(corner[:, 1]))
            
            # Draw ID text with background
            text = f"ID: {marker_id[0]}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            
            # Get text size for background
            (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
            
            # Draw background rectangle
            cv2.rectangle(frame, 
                         (center_x - text_width // 2 - 5, center_y - text_height - 5),
                         (center_x + text_width // 2 + 5, center_y + 5),
                         (0, 0, 0), -1)
            
            # Draw text
            cv2.putText(frame, text, 
                       (center_x - text_width // 2, center_y),
                       font, font_scale, (0, 255, 255), thickness)
    
    return frame

# ============================================================================
# COORDINATE MAPPING FUNCTIONS
# ============================================================================

def pixel_to_grid(cx, cy, frame_width, frame_height, grid_size=5):
    """
    Convert pixel coordinates to grid coordinates
    Returns: (row, col) tuple with values from 0 to grid_size-1
    """
    col = int(cx / (frame_width / grid_size))
    row = int(cy / (frame_height / grid_size))
    
    # Ensure coordinates are within valid range
    col = max(0, min(col, grid_size - 1))
    row = max(0, min(row, grid_size - 1))
    
    return row, col

# ============================================================================
# MAIN TRACKING LOOP
# ============================================================================

def main():
    """Main function to run the object tracking system"""
    
    print("=" * 60)
    print("5×5 GRID OBJECT TRACKING SYSTEM")
    print("=" * 60)
    print(f"Grid Size: {GRID_SIZE}×{GRID_SIZE}")
    print(f"Resolution: {FRAME_WIDTH}×{FRAME_HEIGHT}")
    print(f"Target FPS: {TARGET_FPS}")
    print(f"ArUco Detection: {'ON' if SHOW_ARUCO_MARKERS else 'OFF'}")
    print("\nControls:")
    print("  'q' - Quit application")
    print("  'g' - Toggle grid overlay")
    print("  'h' - Toggle cell highlighting")
    print("  'a' - Toggle ArUco marker detection")
    print("  's' - Save current frame")
    print("=" * 60)
    
    # Initialize webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
    
    if not cap.isOpened():
        print("ERROR: Cannot access camera!")
        return
    
    # Display camera info
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    backend = cap.getBackendName()
    
    print(f"\nCamera {CAMERA_INDEX} initialized successfully!")
    print(f"Resolution: {width}x{height} | Backend: {backend}")
    print("Position your camera directly above the 5×5 grid...")
    print("Ensure the entire grid is visible in the frame.\n")
    
    # Variables for FPS calculation
    fps_start_time = time.time()
    fps_frame_count = 0
    fps_display = 0
    
    # Toggle states
    show_grid = SHOW_GRID_OVERLAY
    show_highlight = SHOW_CELL_HIGHLIGHT
    show_aruco = SHOW_ARUCO_MARKERS
    
    # Previous position for smoothing and change detection
    prev_row, prev_col = None, None
    last_print_time = 0
    print_interval = 0.1  # Print coordinates every 0.1 seconds (10 times per second)
    
    while True:
        # Capture frame
        ret, frame = cap.read()
        
        if not ret:
            print("ERROR: Failed to capture frame!")
            break
        
        height, width = frame.shape[:2]
        
        # Detect object
        cx, cy, area = detect_object(frame, LOWER_HSV, UPPER_HSV, 
                                     LOWER_HSV_ALT, UPPER_HSV_ALT)
        
        # Process detection
        if cx is not None and cy is not None:
            # Convert to grid coordinates
            row, col = pixel_to_grid(cx, cy, width, height, GRID_SIZE)
            
            # Update previous position
            prev_row, prev_col = row, col
            
            # Draw detection circle
            if SHOW_DETECTION_CIRCLE:
                cv2.circle(frame, (cx, cy), 10, (0, 0, 255), -1)
                cv2.circle(frame, (cx, cy), 15, (255, 255, 255), 2)
            
            # Highlight active cell
            if show_highlight:
                frame = highlight_cell(frame, row, col, GRID_SIZE)
            
            # Display coordinates on frame
            coord_text = f"Position: ({row}, {col})"
            cv2.putText(frame, coord_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Display pixel coordinates
            pixel_text = f"Pixel: ({cx}, {cy})"
            cv2.putText(frame, pixel_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Display area
            area_text = f"Area: {int(area)} px"
            cv2.putText(frame, area_text, (10, 85), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Console output - print on new line for real-time tracking
            current_time = time.time()
            if current_time - last_print_time >= print_interval or (row != prev_row or col != prev_col):
                print(f"Grid Position: Row={row}, Col={col} | Pixel: ({cx}, {cy}) | Area: {int(area)}")
                last_print_time = current_time
        
        else:
            # No object detected
            cv2.putText(frame, "No object detected", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            if prev_row is not None and prev_col is not None:
                # Show last known position
                last_pos_text = f"Last: ({prev_row}, {prev_col})"
                cv2.putText(frame, last_pos_text, (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Detect and draw ArUco markers
        if show_aruco:
            aruco_corners, aruco_ids = detect_aruco_markers(frame, ARUCO_DICT)
            frame = draw_aruco_markers(frame, aruco_corners, aruco_ids)
            
            # Print detected ArUco IDs to console
            if aruco_ids is not None and len(aruco_ids) > 0:
                ids_list = [int(id[0]) for id in aruco_ids]
                print(f"ArUco Markers Detected: {ids_list}")
        
        # Draw grid overlay
        if show_grid:
            frame = draw_grid_overlay(frame, GRID_SIZE)
        
        # Calculate and display FPS
        fps_frame_count += 1
        if time.time() - fps_start_time >= 1.0:
            fps_display = fps_frame_count
            fps_frame_count = 0
            fps_start_time = time.time()
        
        if SHOW_FPS:
            cv2.putText(frame, f"FPS: {fps_display}", (width - 120, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Display frame
        cv2.imshow('5x5 Grid Object Tracker', frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\n\nShutting down...")
            break
        elif key == ord('g'):
            show_grid = not show_grid
            print(f"\nGrid overlay: {'ON' if show_grid else 'OFF'}")
        elif key == ord('h'):
            show_highlight = not show_highlight
            print(f"\nCell highlight: {'ON' if show_highlight else 'OFF'}")
        elif key == ord('a'):
            show_aruco = not show_aruco
            print(f"\nArUco detection: {'ON' if show_aruco else 'OFF'}")
        elif key == ord('s'):
            filename = f"capture_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
            print(f"\nFrame saved as {filename}")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Application closed successfully.")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
