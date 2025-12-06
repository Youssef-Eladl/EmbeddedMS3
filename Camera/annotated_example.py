"""
ANNOTATED EXAMPLE: Grid Object Tracking
Educational version with detailed comments explaining every step
This is a simplified, commented version of OpenCV.py for learning

Author: GitHub Copilot
Date: November 2025
"""

import cv2      # OpenCV library for computer vision
import numpy as np  # NumPy for numerical operations and arrays
import time     # For FPS calculation and timing

# ============================================================================
# STEP 1: CONFIGURATION
# Define all constants that control the system behavior
# ============================================================================

# HSV Color Range - These define what color we're looking for
# HSV = Hue (color), Saturation (intensity), Value (brightness)
# For a RED object:
LOWER_HSV = np.array([0, 120, 70])    # Minimum values [H, S, V]
UPPER_HSV = np.array([10, 255, 255])  # Maximum values [H, S, V]

# Red color wraps around in HSV (0-10 and 170-180 both represent red)
LOWER_HSV_ALT = np.array([170, 120, 70])
UPPER_HSV_ALT = np.array([180, 255, 255])

# Grid setup
GRID_SIZE = 5  # We have a 5x5 grid
MIN_OBJECT_AREA = 100  # Minimum size in pixels to be considered valid

# Camera settings
CAMERA_INDEX = 0  # Usually 0 for built-in webcam
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# ============================================================================
# STEP 2: HELPER FUNCTIONS
# These functions do specific tasks in our tracking system
# ============================================================================

def detect_object(frame, lower_hsv, upper_hsv, lower_hsv_alt=None, upper_hsv_alt=None):
    """
    This function finds our colored object in the camera frame.
    
    How it works:
    1. Convert image to HSV color space
    2. Create a mask (white = object color, black = everything else)
    3. Clean up the mask to remove noise
    4. Find the object outline (contour)
    5. Calculate the center point (centroid)
    
    Returns:
        cx, cy: Center coordinates in pixels (or None if not found)
        area: Size of detected object in pixels
    """
    
    # Convert from BGR (default camera format) to HSV
    # HSV is better because lighting changes don't affect Hue as much
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Create a binary mask: pixels in our color range = white (255), others = black (0)
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
    
    # If we have an alternative range (for red), add it to the mask
    if lower_hsv_alt is not None and upper_hsv_alt is not None:
        mask_alt = cv2.inRange(hsv, lower_hsv_alt, upper_hsv_alt)
        mask = cv2.bitwise_or(mask, mask_alt)  # Combine both masks
    
    # Clean up the mask using morphological operations
    kernel = np.ones((5, 5), np.uint8)  # 5x5 structuring element
    
    # MORPH_OPEN: Removes small white noise (erosion then dilation)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # MORPH_CLOSE: Fills small black holes (dilation then erosion)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours (boundaries) of white regions in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # If no contours found, return None
    if len(contours) == 0:
        return None, None, 0
    
    # Find the largest contour (assume this is our object)
    largest_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_contour)
    
    # If the area is too small, it's probably noise - ignore it
    if area < MIN_OBJECT_AREA:
        return None, None, 0
    
    # Calculate the centroid (center point) using image moments
    # Moments are mathematical properties that describe the shape
    M = cv2.moments(largest_contour)
    
    # The centroid formula: cx = M10/M00, cy = M01/M00
    if M["m00"] != 0:  # Avoid division by zero
        cx = int(M["m10"] / M["m00"])  # X coordinate
        cy = int(M["m01"] / M["m00"])  # Y coordinate
        return cx, cy, area
    
    return None, None, 0


def pixel_to_grid(cx, cy, frame_width, frame_height, grid_size=5):
    """
    Convert pixel coordinates to grid cell coordinates.
    
    Example: If frame is 640x480 and we have 5x5 grid:
    - Each cell is 128 pixels wide (640/5) and 96 pixels tall (480/5)
    - Pixel (384, 192) is in cell (2, 3) because:
      - col = 384 / 128 = 3
      - row = 192 / 96 = 2
    
    Args:
        cx, cy: Pixel coordinates
        frame_width, frame_height: Frame dimensions
        grid_size: Number of cells per side (5 for 5x5)
    
    Returns:
        row, col: Grid coordinates (0 to grid_size-1)
    """
    
    # Calculate which column the x-coordinate falls in
    col = int(cx / (frame_width / grid_size))
    
    # Calculate which row the y-coordinate falls in
    row = int(cy / (frame_height / grid_size))
    
    # Make sure we don't go out of bounds (keep between 0 and grid_size-1)
    col = max(0, min(col, grid_size - 1))
    row = max(0, min(row, grid_size - 1))
    
    return row, col


def draw_grid_overlay(frame, grid_size=5):
    """
    Draw white grid lines on the camera frame.
    This helps visualize the 5x5 grid alignment.
    """
    height, width = frame.shape[:2]  # Get frame dimensions
    
    # Calculate cell dimensions
    cell_width = width // grid_size   # // is integer division
    cell_height = height // grid_size
    
    # Draw vertical lines
    for i in range(1, grid_size):  # 1 to 4 (we have 4 interior lines)
        x = i * cell_width
        # Draw line from top to bottom
        cv2.line(frame, (x, 0), (x, height), (255, 255, 255), 2)
    
    # Draw horizontal lines
    for i in range(1, grid_size):
        y = i * cell_height
        # Draw line from left to right
        cv2.line(frame, (0, y), (width, y), (255, 255, 255), 2)
    
    return frame


def highlight_cell(frame, row, col, grid_size=5):
    """
    Highlight the cell where the object is currently located.
    Draws a semi-transparent green overlay on the active cell.
    """
    height, width = frame.shape[:2]
    cell_width = width // grid_size
    cell_height = height // grid_size
    
    # Calculate cell boundaries
    x1 = col * cell_width   # Left edge
    y1 = row * cell_height  # Top edge
    x2 = x1 + cell_width    # Right edge
    y2 = y1 + cell_height   # Bottom edge
    
    # Create a copy to draw the semi-transparent overlay
    overlay = frame.copy()
    
    # Draw filled green rectangle on the overlay
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)
    
    # Blend overlay with original (30% overlay, 70% original)
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    
    # Draw green border around the cell
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
    
    return frame


# ============================================================================
# STEP 3: MAIN TRACKING LOOP
# This is where everything comes together
# ============================================================================

def main():
    """
    Main function that runs the tracking system.
    This continuously captures frames and tracks the object.
    """
    
    print("=" * 60)
    print("5x5 GRID OBJECT TRACKER - ANNOTATED VERSION")
    print("=" * 60)
    print("Controls: 'q' to quit, 'g' to toggle grid, 's' to save frame")
    print("=" * 60)
    
    # Open the camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print("ERROR: Could not open camera!")
        return
    
    print("Camera opened successfully!")
    print("Position your camera above the grid and start tracking...\n")
    
    # Variables for FPS calculation
    fps_start_time = time.time()
    fps_counter = 0
    fps_display = 0
    
    # Toggle for grid overlay
    show_grid = True
    
    # Main loop - runs continuously until user presses 'q'
    while True:
        
        # STEP A: Capture frame from camera
        ret, frame = cap.read()  # ret = success/failure, frame = image
        
        if not ret:
            print("Failed to grab frame!")
            break
        
        height, width = frame.shape[:2]  # Get dimensions
        
        # STEP B: Detect the object in this frame
        cx, cy, area = detect_object(frame, LOWER_HSV, UPPER_HSV, 
                                     LOWER_HSV_ALT, UPPER_HSV_ALT)
        
        # STEP C: Process the detection results
        if cx is not None and cy is not None:
            # Object was found!
            
            # Convert pixel position to grid coordinates
            row, col = pixel_to_grid(cx, cy, width, height, GRID_SIZE)
            
            # Draw a red circle at the detected center point
            cv2.circle(frame, (cx, cy), 10, (0, 0, 255), -1)  # Filled circle
            cv2.circle(frame, (cx, cy), 15, (255, 255, 255), 2)  # White outline
            
            # Highlight the active cell
            frame = highlight_cell(frame, row, col, GRID_SIZE)
            
            # Display grid coordinates on the frame
            coord_text = f"Position: ({row}, {col})"
            cv2.putText(frame, coord_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Display pixel coordinates (for debugging)
            pixel_text = f"Pixel: ({cx}, {cy})"
            cv2.putText(frame, pixel_text, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Print to console (use end='\r' to overwrite same line)
            print(f"Object at Grid ({row}, {col}) | Pixels ({cx}, {cy}) | Area: {int(area)}    ", end='\r')
        
        else:
            # Object not found
            cv2.putText(frame, "No object detected", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # STEP D: Draw grid overlay if enabled
        if show_grid:
            frame = draw_grid_overlay(frame, GRID_SIZE)
        
        # STEP E: Calculate and display FPS
        fps_counter += 1
        if time.time() - fps_start_time >= 1.0:  # Every second
            fps_display = fps_counter
            fps_counter = 0
            fps_start_time = time.time()
        
        cv2.putText(frame, f"FPS: {fps_display}", (width - 100, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # STEP F: Display the frame in a window
        cv2.imshow('Grid Object Tracker', frame)
        
        # STEP G: Check for keyboard input
        key = cv2.waitKey(1) & 0xFF  # Wait 1ms for a key press
        
        if key == ord('q'):  # Quit
            print("\n\nQuitting...")
            break
        
        elif key == ord('g'):  # Toggle grid
            show_grid = not show_grid
            print(f"\nGrid overlay: {'ON' if show_grid else 'OFF'}")
        
        elif key == ord('s'):  # Save frame
            filename = f"frame_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
            print(f"\nSaved: {filename}")
    
    # STEP H: Cleanup
    cap.release()  # Release the camera
    cv2.destroyAllWindows()  # Close all windows
    print("Tracker closed successfully.")


# ============================================================================
# ENTRY POINT
# This runs when you execute the script
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# EXPLANATION OF KEY CONCEPTS
# ============================================================================

"""
1. COLOR SPACES:
   - BGR: Default camera format (Blue, Green, Red)
   - HSV: Better for color detection (Hue, Saturation, Value)
   - We use HSV because Hue is independent of lighting

2. BINARY MASK:
   - Black and white image
   - White (255) = object color
   - Black (0) = everything else
   - Created by cv2.inRange()

3. MORPHOLOGICAL OPERATIONS:
   - MORPH_OPEN: Removes small noise
   - MORPH_CLOSE: Fills holes
   - Uses a kernel (structuring element) to process the image

4. CONTOURS:
   - Boundaries of white regions in binary mask
   - We find the largest one (assumes it's our object)
   - Can extract many features: area, perimeter, centroid, etc.

5. IMAGE MOMENTS:
   - Mathematical properties of an image region
   - M["m00"] = area (total white pixels)
   - M["m10"]/M["m00"] = x coordinate of centroid
   - M["m01"]/M["m00"] = y coordinate of centroid
   - Centroid = "center of mass" of the detected region

6. COORDINATE MAPPING:
   - Divide frame into logical 5x5 grid
   - Each cell is (width/5) x (height/5) pixels
   - Integer division gives us grid cell indices
   - Example: pixel 384 / (640/5) = 384/128 = 3 (column 3)

7. FRAME RATE:
   - We count frames per second (FPS)
   - Higher FPS = smoother tracking
   - Typical: 25-30 FPS on standard laptop
   - Limited by camera speed and processing time

8. EVENT LOOP:
   - Continuously capture frames
   - Process each frame
   - Display results
   - Check for user input
   - Repeat until 'q' is pressed
"""

# ============================================================================
# TROUBLESHOOTING TIPS
# ============================================================================

"""
Problem: Camera doesn't open
Solution: Change CAMERA_INDEX to 1 or 2

Problem: Object not detected
Solution: 
  1. Run hsv_calibration.py to find correct HSV range
  2. Improve lighting
  3. Use more contrasting color

Problem: False detections
Solution:
  1. Narrow HSV range (adjust S and V)
  2. Increase MIN_OBJECT_AREA
  3. Remove background objects with similar colors

Problem: Slow frame rate
Solution:
  1. Reduce FRAME_WIDTH and FRAME_HEIGHT
  2. Close other applications
  3. Use smaller kernel for morphology

Problem: Coordinates jumping around
Solution:
  1. Stabilize camera
  2. Improve lighting consistency
  3. Increase MIN_OBJECT_AREA
  4. Add smoothing (moving average)
"""
