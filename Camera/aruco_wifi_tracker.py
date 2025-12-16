"""
Aruco Marker Serial Tracking System for Forge Registry Station
Tracks Aruco markers on 5x5 grid and streams coordinates to the Pico over USB serial
Author: GitHub Copilot
Date: December 2025
"""

import cv2
import numpy as np
import time
import serial
import serial.tools.list_ports
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    print("WARNING: pytesseract not installed. OCR number detection disabled.")
    print("Install with: pip install pytesseract")
    TESSERACT_AVAILABLE = False

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# Serial Configuration
SERIAL_PORT = "COM3"      # Change to the Pico's COM port (e.g., COM5 on Windows, /dev/ttyACM0 on Linux)
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 0.01      # Seconds

# Grid Configuration
GRID_SIZE = 5  # 5x5 grid

# Camera Configuration
CAMERA_INDEX = 1  # 0 for default webcam, 1 for external camera
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# ArUco Configuration
ARUCO_DICT = cv2.aruco.DICT_4X4_50  # ArUco dictionary type
MIN_MARKER_AREA = 1000  # Minimum marker area in pixels

# Red Blob Detection (Electromagnet)
LOWER_RED_HSV = np.array([0, 120, 70])    # Lower red hue range
UPPER_RED_HSV = np.array([10, 255, 255])
LOWER_RED_HSV_ALT = np.array([170, 120, 70])  # Upper red hue range (wraps around)
UPPER_RED_HSV_ALT = np.array([180, 255, 255])
MIN_BLOB_AREA = 100  # Minimum blob area in pixels
VERIFY_DURATION = 5.0  # Hold target position for 5 seconds

# Display Configuration
SHOW_GRID_OVERLAY = True
SHOW_FPS = True
SEND_INTERVAL = 0.1  # Send updates every 100ms (10Hz)

# Grid Configuration
MANUAL_GRID_MODE = False     # Manual grid corner selection (press 'm' to activate)

# Manual grid calibration points (top-left and bottom-right corners)
manual_grid_corners = []

# ============================================================================
# OCR NUMBER DETECTION
# ============================================================================

def detect_4digit_number(frame):
    """Detect a 4-digit number written in black ink on paper using OCR"""
    if not TESSERACT_AVAILABLE:
        return None
    
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to isolate black text on white/light background
        # Invert so text is white on black background (better for OCR)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Configure tesseract to only recognize digits
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        
        # Run OCR
        text = pytesseract.image_to_string(thresh, config=custom_config)
        
        # Extract 4-digit numbers from detected text
        import re
        matches = re.findall(r'\b\d{4}\b', text)
        
        if matches:
            # Return the first 4-digit number found
            number = matches[0]
            print(f"OCR detected number: {number}")
            return number
        
        return None
    except Exception as e:
        print(f"ERROR: OCR failed - {e}")
        print("Tesseract may not be installed. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
        return None

def parse_target_coords(number_str):
    """Parse 4-digit string into two coordinate pairs
    Example: '4235' -> plate1=(4,2), plate2=(3,5)
    Returns: (plate1_row, plate1_col, plate2_row, plate2_col) in 0-indexed
    """
    if len(number_str) != 4:
        return None
    
    try:
        # Parse digits
        d1 = int(number_str[0])  # Plate 1 row (1-indexed)
        d2 = int(number_str[1])  # Plate 1 col (1-indexed)
        d3 = int(number_str[2])  # Plate 2 row (1-indexed)
        d4 = int(number_str[3])  # Plate 2 col (1-indexed)
        
        # Convert to 0-indexed and validate (must be 1-5 in 1-indexed = 0-4 in 0-indexed)
        if not all(1 <= d <= 5 for d in [d1, d2, d3, d4]):
            print(f"ERROR: All digits must be 1-5 for a 5x5 grid. Got: {number_str}")
            return None
        
        # Convert to 0-indexed
        plate1_row = d1 - 1
        plate1_col = d2 - 1
        plate2_row = d3 - 1
        plate2_col = d4 - 1
        
        print(f"Parsed coordinates:")
        print(f"  Plate 1 target: ({d1},{d2}) [0-indexed: ({plate1_row},{plate1_col})]")
        print(f"  Plate 2 target: ({d3},{d4}) [0-indexed: ({plate2_row},{plate2_col})]")
        
        return (plate1_row, plate1_col, plate2_row, plate2_col)
    except ValueError:
        print(f"ERROR: Failed to parse number: {number_str}")
        return None

# ============================================================================
# MANUAL GRID CALIBRATION
# ============================================================================

def mouse_callback(event, x, y, flags, param):
    """Mouse callback for manual grid corner selection"""
    global manual_grid_corners
    
    if event == cv2.EVENT_LBUTTONDOWN and MANUAL_GRID_MODE:
        if len(manual_grid_corners) < 2:
            manual_grid_corners.append((x, y))
            print(f"Corner {len(manual_grid_corners)} set at: ({x}, {y})")
            if len(manual_grid_corners) == 2:
                print("Grid calibration complete! Press 'c' to confirm or 'r' to reset.")

def create_manual_grid(frame_width, frame_height):
    """Create grid lines from two corner points"""
    if len(manual_grid_corners) != 2:
        return None, None
    
    # Get corners
    (x1, y1) = manual_grid_corners[0]
    (x2, y2) = manual_grid_corners[1]
    
    # Ensure top-left to bottom-right
    x_min, x_max = min(x1, x2), max(x1, x2)
    y_min, y_max = min(y1, y2), max(y1, y2)
    
    # Create 6 evenly spaced vertical and horizontal lines
    v_lines = [x_min + i * (x_max - x_min) / 5 for i in range(6)]
    h_lines = [y_min + i * (y_max - y_min) / 5 for i in range(6)]
    
    return v_lines, h_lines

# ============================================================================
# GRID FUNCTIONS
# ============================================================================

def pixel_to_grid_calibrated(cx, cy, v_lines, h_lines):
    """
    Convert pixel coordinates to grid coordinates using detected grid lines
    Returns: (row, col) tuple with values from 0 to grid_size-1
    """
    if v_lines is None or h_lines is None:
        return None, None
    
    # Find which cell the point is in
    col = None
    for i in range(len(v_lines) - 1):
        if v_lines[i] <= cx < v_lines[i + 1]:
            col = i
            break
    
    row = None
    for i in range(len(h_lines) - 1):
        if h_lines[i] <= cy < h_lines[i + 1]:
            row = i
            break
    
    # Clamp to valid range
    if col is not None and row is not None:
        col = max(0, min(col, GRID_SIZE - 1))
        row = max(0, min(row, GRID_SIZE - 1))
    
    return row, col

def draw_detected_grid(frame, v_lines, h_lines):
    """Draw the detected grid lines on the frame"""
    if v_lines is None or h_lines is None:
        return frame
    
    # Draw vertical lines
    for x in v_lines:
        cv2.line(frame, (int(x), 0), (int(x), frame.shape[0]), (0, 255, 0), 2)
    
    # Draw horizontal lines
    for y in h_lines:
        cv2.line(frame, (0, int(y)), (frame.shape[1], int(y)), (0, 255, 0), 2)
    
    # Draw cell labels
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            if row < len(h_lines) - 1 and col < len(v_lines) - 1:
                x_center = int((v_lines[col] + v_lines[col + 1]) / 2)
                y_center = int((h_lines[row] + h_lines[row + 1]) / 2)
                label = f"({row+1},{col+1})"
                cv2.putText(frame, label, (x_center - 30, y_center), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    return frame

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
    
    # Draw cell labels (1-indexed for user display)
    for row in range(grid_size):
        for col in range(grid_size):
            x = col * cell_width + cell_width // 2
            y = row * cell_height + cell_height // 2
            label = f"({row+1},{col+1})"
            cv2.putText(frame, label, (x - 35, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
    
    return frame

def highlight_cell(frame, row, col, grid_size=5, color=(0, 255, 0)):
    """Highlight a specific cell where a marker is located"""
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
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    
    # Draw cell border
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
    
    return frame

# ============================================================================
# ARUCO MARKER DETECTION FUNCTIONS
# ============================================================================

def detect_aruco_markers(frame, aruco_dict_type):
    """
    Detect ArUco markers in the frame
    Returns: list of marker IDs, corner coordinates, and centers
    """
    # Load ArUco dictionary and parameters
    aruco_dict = cv2.aruco.getPredefinedDictionary(aruco_dict_type)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
    
    # Detect markers
    corners, ids, rejected = detector.detectMarkers(frame)
    
    marker_data = []
    
    if ids is not None and len(ids) > 0:
        for i, marker_id in enumerate(ids):
            # Get corner coordinates
            corner = corners[i][0]
            
            # Calculate marker center
            center_x = int(np.mean(corner[:, 0]))
            center_y = int(np.mean(corner[:, 1]))
            
            # Calculate marker area (approximate)
            area = cv2.contourArea(corner)
            
            # Only include markers above minimum area threshold
            if area >= MIN_MARKER_AREA:
                marker_data.append({
                    'id': int(marker_id[0]),
                    'center_x': center_x,
                    'center_y': center_y,
                    'corners': corner.tolist(),
                    'area': area
                })
    
    return corners, ids, marker_data

def draw_aruco_markers(frame, corners, ids, marker_data):
    """Draw detected ArUco markers on the frame with IDs and grid positions"""
    if ids is not None and len(ids) > 0:
        # Draw marker boundaries
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        
        # Add ID labels and grid positions at marker centers
        for data in marker_data:
            center_x = data['center_x']
            center_y = data['center_y']
            marker_id = data['id']
            
            # Draw center point
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            
            # Draw ID text with background
            text = f"ID: {marker_id}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.9
            thickness = 2
            
            # Get text size for background
            (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
            
            # Draw background rectangle
            cv2.rectangle(frame, 
                         (center_x - text_width // 2 - 5, center_y - text_height - 10),
                         (center_x + text_width // 2 + 5, center_y - 5),
                         (0, 0, 0), -1)
            
            # Draw text
            cv2.putText(frame, text, 
                       (center_x - text_width // 2, center_y - 10),
                       font, font_scale, (0, 255, 255), thickness)
            
            # Draw grid position below ID
            if 'grid_row' in data and 'grid_col' in data and data['grid_row'] is not None and data['grid_col'] is not None:
                grid_text = f"({data['grid_row']+1},{data['grid_col']+1})"
                cv2.putText(frame, grid_text, 
                           (center_x - 30, center_y + 30),
                           font, 0.7, (255, 255, 0), 2)
    
    return frame

# ============================================================================
# RED BLOB DETECTION (ELECTROMAGNET TRACKING)
# ============================================================================

def detect_red_blob(frame):
    """
    Detect red blob (electromagnet) in the frame
    Returns: (cx, cy, area) if found, or (None, None, 0) if not found
    """
    # Convert to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Create masks for both red hue ranges (red wraps around in HSV)
    mask1 = cv2.inRange(hsv, LOWER_RED_HSV, UPPER_RED_HSV)
    mask2 = cv2.inRange(hsv, LOWER_RED_HSV_ALT, UPPER_RED_HSV_ALT)
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Morphological operations to reduce noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, None, 0
    
    # Find largest contour
    largest_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_contour)
    
    # Check minimum area threshold
    if area < MIN_BLOB_AREA:
        return None, None, 0
    
    # Calculate centroid
    M = cv2.moments(largest_contour)
    if M["m00"] == 0:
        return None, None, 0
    
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    
    return cx, cy, area

def draw_red_blob(frame, cx, cy, row, col, verified=False, progress=0.0):
    """Draw red blob detection visualization on frame"""
    if cx is None or cy is None:
        return frame
    
    # Draw crosshair at blob center
    color = (0, 255, 0) if verified else (0, 0, 255)
    cv2.drawMarker(frame, (cx, cy), color, cv2.MARKER_CROSS, 20, 2)
    
    # Draw circle around blob
    cv2.circle(frame, (cx, cy), 15, color, 2)
    
    # Draw grid position
    if row is not None and col is not None:
        text = f"Magnet: ({row+1},{col+1})"
        cv2.putText(frame, text, (cx + 25, cy - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    # Draw verification progress bar
    if progress > 0:
        bar_width = 100
        bar_height = 10
        bar_x = cx - bar_width // 2
        bar_y = cy + 25
        
        # Background
        cv2.rectangle(frame, (bar_x, bar_y), 
                     (bar_x + bar_width, bar_y + bar_height), 
                     (100, 100, 100), -1)
        
        # Progress fill
        fill_width = int(bar_width * progress)
        cv2.rectangle(frame, (bar_x, bar_y),
                     (bar_x + fill_width, bar_y + bar_height),
                     (0, 255, 0), -1)
        
        # Border
        cv2.rectangle(frame, (bar_x, bar_y),
                     (bar_x + bar_width, bar_y + bar_height),
                     (255, 255, 255), 1)
        
        # Progress text
        percent_text = f"{int(progress * 100)}%"
        cv2.putText(frame, percent_text, (bar_x + bar_width + 5, bar_y + bar_height),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    return frame

# ============================================================================
# COORDINATE MAPPING FUNCTIONS
# ============================================================================

def pixel_to_grid(cx, cy, frame_width, frame_height, grid_size=5):
    """
    Convert pixel coordinates to grid coordinates (0-indexed)
    Returns: (row, col) tuple with values from 0 to grid_size-1
    """
    col = int(cx / (frame_width / grid_size))
    row = int(cy / (frame_height / grid_size))
    
    # Ensure coordinates are within valid range
    col = max(0, min(col, grid_size - 1))
    row = max(0, min(row, grid_size - 1))
    
    return row, col

# ============================================================================
# SERIAL COMMUNICATION FUNCTIONS
# ============================================================================

def pick_serial_port(preferred):
    """Try preferred port, otherwise suggest available ones."""
    ports = list(serial.tools.list_ports.comports())
    names = [p.device for p in ports]
    if preferred in names:
        return preferred, names
    return (names[0] if names else None), names


def open_serial(port, baud):
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=SERIAL_TIMEOUT)
        print(f"Serial connected on {port} @ {baud} baud")
        return ser
    except Exception as e:
        print(f"ERROR opening serial port '{port}': {e}")
        return None


def send_marker_data(ser, marker_data_list):
    """Send the first detected marker as CSV: id,row,col
"""
    if ser is None:
        return False
    if not marker_data_list:
        return False

    # Choose the largest marker to prioritize the closest/clearest
    primary = sorted(marker_data_list, key=lambda m: m.get('area', 0), reverse=True)[0]
    line = f"{primary['id']},{primary['grid_row']},{primary['grid_col']}\n"
    try:
        ser.write(line.encode('utf-8'))
        ser.flush()
        return True
    except Exception as e:
        print(f"ERROR writing to serial: {e}")
        return False

def send_release_command(ser):
    """Send release command to Pico: RELEASE
"""
    if ser is None:
        return False
    try:
        ser.write(b"RELEASE\n")
        ser.flush()
        print("Sent RELEASE command to Pico")
        return True
    except Exception as e:
        print(f"ERROR sending release: {e}")
        return False

def send_blob_position(ser, marker_id, row, col):
    """Send current blob position to Pico for real-time LCD update.
    Format: id,row,col (same as marker data format)
    This is used during movement to update the Pico about current position.
    """
    if ser is None:
        return False
    if row is None or col is None:
        return False
    try:
        line = f"{marker_id},{row},{col}\n"
        ser.write(line.encode('utf-8'))
        ser.flush()
        return True
    except Exception as e:
        print(f"ERROR sending blob position: {e}")
        return False

def send_pickup_command(ser, marker_id, target_row, target_col):
    """Send pickup command to Pico: PICKUP,id,target_row,target_col
    """
    if ser is None:
        return False
    try:
        command = f"PICKUP,{marker_id},{target_row},{target_col}\n"
        ser.write(command.encode('utf-8'))
        ser.flush()
        print(f"Sent PICKUP command for marker ID {marker_id} -> target ({target_row+1},{target_col+1})")
        return True
    except Exception as e:
        print(f"ERROR sending pickup: {e}")
        return False

class PositionVerifier:
    """Tracks if red blob stays at target position for required duration"""
    def __init__(self, duration=5.0):
        self.duration = duration
        self.target_row = None
        self.target_col = None
        self.start_time = None
        self.verified = False
        
    def set_target(self, row, col):
        """Set the target position to verify"""
        self.target_row = row
        self.target_col = col
        self.start_time = None
        self.verified = False
        
    def update(self, current_row, current_col):
        """
        Update verification state with current position
        Returns True if position held for full duration
        """
        if self.target_row is None or self.verified:
            return self.verified
            
        if current_row == self.target_row and current_col == self.target_col:
            if self.start_time is None:
                self.start_time = time.time()
            elif time.time() - self.start_time >= self.duration:
                self.verified = True
                return True
        else:
            # Moved away from target
            self.start_time = None
            
        return False
    
    def get_progress(self):
        """Get verification progress (0.0 to 1.0)"""
        if self.start_time is None:
            return 0.0
        elapsed = time.time() - self.start_time
        return min(elapsed / self.duration, 1.0)
    
    def reset(self):
        """Reset verification state"""
        self.target_row = None
        self.target_col = None
        self.start_time = None
        self.verified = False

# ============================================================================
# MAIN TRACKING LOOP
# ============================================================================

def main():
    """Main function to run the Aruco tracking system"""
    
    global MANUAL_GRID_MODE, manual_grid_corners
    
    print("=" * 70)
    print("ARUCO MARKER SERIAL TRACKER - FORGE REGISTRY STATION")
    print("=" * 70)
    print(f"Grid Size: {GRID_SIZE}×{GRID_SIZE}")
    print(f"Resolution: {FRAME_WIDTH}×{FRAME_HEIGHT}")
    print(f"Target FPS: {TARGET_FPS}")
    print(f"Serial Port: {SERIAL_PORT} @ {SERIAL_BAUD}")
    print(f"Send Rate: {int(1/SEND_INTERVAL)} Hz")
    print("\nControls:")
    print("  'q' - Quit application")
    print("  'g' - Toggle grid overlay")
    print("  's' - Save current frame")
    print("  'm' - Toggle manual grid mode (click 2 corners)")
    print("  'c' - Confirm manual grid")
    print("  'r' - Reset manual grid")
    print("=" * 70)
    
    # Initialize serial (test mode if not available)
    test_mode = False
    ser = None
    
    port, available = pick_serial_port(SERIAL_PORT)
    if port is None:
        print("\nWARNING: No serial ports found.")
        print("*** RUNNING IN TEST MODE - No data will be sent to Pico ***\n")
        test_mode = True
    else:
        if port != SERIAL_PORT:
            print(f"Using detected port: {port} (preferred {SERIAL_PORT}). Available: {available}")
        ser = open_serial(port, SERIAL_BAUD)
        if ser is None:
            print("\nWARNING: Failed to open serial port.")
            print(f"*** RUNNING IN TEST MODE - No data will be sent to Pico ***\n")
            test_mode = True
        else:
            print(f"Serial connection established on {port}")
    
    # Initialize webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
    
    if not cap.isOpened():
        print("ERROR: Cannot access camera!")
        if ser:
            ser.close()
        return
    
    # Display camera info
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    backend = cap.getBackendName()
    
    print(f"\nCamera {CAMERA_INDEX} initialized successfully!")
    print(f"Resolution: {width}x{height} | Backend: {backend}")
    print("Position your camera directly above the 5×5 grid...")
    print("Tracking Aruco markers...\n")
    
    # Variables for FPS calculation
    fps_start_time = time.time()
    fps_frame_count = 0
    fps_display = 0
    
    # Toggle states
    show_grid = SHOW_GRID_OVERLAY
    
    # Send timing
    last_send_time = 0
    
    # Pico status
    pico_status = "WAITING"
    
    # Position verifier for red blob
    verifier = PositionVerifier(duration=VERIFY_DURATION)
    blob_verified = False
    
    # Workflow state for multi-plate system
    pickup_initiated = False
    active_marker_id = None
    target_position = None  # (row, col) where marker should be placed
    plates_completed = 0  # Track how many plates have been placed
    max_plates = 2  # Support 2 plates
    workflow_complete = False
    detected_marker_ids = set()  # Track IDs already detected to prevent duplicates
    
    # Grid calibration
    v_lines = None
    h_lines = None
    grid_calibrated = False
    calibration_frames = 0
    manual_confirmed = False
    
    # Set up mouse callback for manual grid selection
    cv2.namedWindow('Aruco WiFi Tracker - Forge Registry', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Aruco WiFi Tracker - Forge Registry', 800, 600)
    cv2.setMouseCallback('Aruco WiFi Tracker - Forge Registry', mouse_callback)
    
    # OCR Number Detection Phase
    plate1_target = None
    plate2_target = None
    number_detected = False
    
    if TESSERACT_AVAILABLE:
        print("\n" + "="*70)
        print("STEP 1: NUMBER DETECTION")
        print("="*70)
        print("Place a paper with a 4-digit number (e.g., 4235) in view.")
        print("  - First 2 digits = Plate 1 target coordinates (row, col)")
        print("  - Last 2 digits = Plate 2 target coordinates (row, col)")
        print("  - All digits must be 1-5 for the 5x5 grid")
        print("Press 'n' when ready to detect the number, or 's' to skip...\n")
        
        while not number_detected:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Failed to capture frame!")
                break
            
            # Show preview
            preview = frame.copy()
            cv2.putText(preview, "Place 4-digit number in view", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(preview, "Press 'n' to detect, 's' to skip", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow('Aruco WiFi Tracker - Forge Registry', preview)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('n'):
                # Attempt detection
                print("\nDetecting number...")
                number_str = detect_4digit_number(frame)
                if number_str:
                    coords = parse_target_coords(number_str)
                    if coords:
                        plate1_target = (coords[0], coords[1])
                        plate2_target = (coords[2], coords[3])
                        number_detected = True
                        print(f"\n*** NUMBER DETECTED: {number_str} ***")
                        print(f"Plate 1 -> ({coords[0]+1},{coords[1]+1})")
                        print(f"Plate 2 -> ({coords[2]+1},{coords[3]+1})\n")
                    else:
                        print("Invalid coordinates detected. Try again or press 's' to skip.")
                else:
                    print("No 4-digit number detected. Try again or press 's' to skip.")
            elif key == ord('s'):
                print("\nSkipping number detection - using default targets\n")
                break
            elif key == ord('q'):
                print("\nQuitting...")
                cap.release()
                cv2.destroyAllWindows()
                if ser:
                    ser.close()
                return
    else:
        print("\nWARNING: Tesseract OCR not available - using default target positions\n")
    
    # Use defaults if not detected
    if plate1_target is None:
        plate1_target = (4, 1)  # Default: position (5,2) in 1-indexed from "5234"
        plate2_target = (2, 3)  # Default: position (3,4) in 1-indexed from "5234"
        print(f"Using default targets: Plate1=({plate1_target[0]+1},{plate1_target[1]+1}), Plate2=({plate2_target[0]+1},{plate2_target[1]+1})")
    
    while True:
        # Capture frame
        ret, frame = cap.read()
        
        if not ret:
            print("ERROR: Failed to capture frame!")
            break
        
        height, width = frame.shape[:2]
        
        # Manual grid mode
        if manual_confirmed and len(manual_grid_corners) == 2:
            v_lines, h_lines = create_manual_grid(width, height)
            if v_lines is not None:
                grid_calibrated = True
                print(f"\n*** MANUAL GRID CALIBRATED ***")
                print(f"Grid corners: {manual_grid_corners}\n")
                manual_confirmed = False  # Only print once
        
        # Draw manual calibration points
        if MANUAL_GRID_MODE:
            for i, (x, y) in enumerate(manual_grid_corners):
                cv2.circle(frame, (x, y), 10, (0, 255, 255), -1)
                cv2.putText(frame, f"Corner {i+1}", (x + 15, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            if len(manual_grid_corners) == 2 and not manual_confirmed:
                cv2.putText(frame, "Press 'c' to confirm grid", (10, height - 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Detect ArUco markers
        corners, ids, marker_data = detect_aruco_markers(frame, ARUCO_DICT)
        
        # Add grid coordinates to marker data (only if grid is calibrated)
        for data in marker_data:
            if v_lines is not None and h_lines is not None:
                # Use detected grid lines to determine grid slot
                row, col = pixel_to_grid_calibrated(data['center_x'], data['center_y'], v_lines, h_lines)
                data['grid_row'] = row
                data['grid_col'] = col
            else:
                # No grid detected - cannot assign grid position
                data['grid_row'] = None
                data['grid_col'] = None
        
        # Check for ArUco at position (1,1) to initiate pickup
        if not pickup_initiated and marker_data and grid_calibrated:
            for data in marker_data:
                # Position (1,1) in 1-indexed = (0,0) in 0-indexed
                # Skip if this marker ID was already detected/used
                if data['grid_row'] == 0 and data['grid_col'] == 0 and data['id'] not in detected_marker_ids:
                    pickup_initiated = True
                    active_marker_id = data['id']
                    detected_marker_ids.add(data['id'])  # Mark this ID as used
                    
                    # Use detected target coordinates based on which plate we're on
                    if plates_completed == 0:
                        target_row, target_col = plate1_target
                    else:
                        target_row, target_col = plate2_target
                    
                    target_position = (target_row, target_col)
                    
                    if not test_mode:
                        send_pickup_command(ser, active_marker_id, target_row, target_col)
                    print(f"\n*** PICKUP INITIATED: Marker {active_marker_id} at (1,1) ***")
                    print(f"*** Target position: ({target_row+1},{target_col+1}) ***\n")
                    
                    # Set target for blob verification
                    verifier.set_target(target_row, target_col)
                    break
        
        # Detect red blob (electromagnet)
        blob_cx, blob_cy, blob_area = detect_red_blob(frame)
        blob_row, blob_col = None, None
        
        if blob_cx is not None:
            # Use detected grid lines to determine blob position
            if v_lines is not None and h_lines is not None:
                blob_row, blob_col = pixel_to_grid_calibrated(blob_cx, blob_cy, v_lines, h_lines)
            # If no grid detected, blob position is unknown
            
            # Verify blob position if pickup has been initiated
            if pickup_initiated and not blob_verified and target_position is not None:
                target_row, target_col = target_position
                
                # Update verifier with current blob position
                if verifier.update(blob_row, blob_col):
                    # Blob has been at target for full duration
                    blob_verified = True
                    plates_completed += 1
                    if not test_mode:
                        send_release_command(ser)
                        print(f"\n*** VERIFIED: Blob held at ({target_row+1},{target_col+1}) for {VERIFY_DURATION}s - RELEASE sent ***\n")
                    else:
                        print(f"\n*** VERIFIED: Blob held at ({target_row+1},{target_col+1}) for {VERIFY_DURATION}s - (TEST MODE) ***\n")
                    
                    # Reset for next plate if not complete
                    if plates_completed < max_plates:
                        print(f"\n*** Plate {plates_completed}/{max_plates} complete. Waiting for next ArUco at (1,1)... ***\n")
                        pickup_initiated = False
                        active_marker_id = None
                        target_position = None
                        blob_verified = False
                        verifier.reset()
                    else:
                        print(f"\n*** ALL {max_plates} PLATES COMPLETE! ***\n")
                        workflow_complete = True
        
        # Send data to Pico at specified interval (only after grid is calibrated)
        current_time = time.time()
        if grid_calibrated and current_time - last_send_time >= SEND_INTERVAL:
            if pickup_initiated and active_marker_id is not None and blob_row is not None:
                # During pickup/movement: send BLOB position for real-time LCD update
                if not test_mode:
                    success = send_blob_position(ser, active_marker_id, blob_row, blob_col)
                    pico_status = f"BLOB ({blob_row+1},{blob_col+1})" if success else "BLOB FAILED"
                else:
                    pico_status = f"BLOB TEST ({blob_row+1},{blob_col+1})"
            elif marker_data:
                # Before pickup: send ArUco marker data
                if not test_mode:
                    success = send_marker_data(ser, marker_data)
                    pico_status = "SENT" if success else "FAILED"
                else:
                    pico_status = "TEST MODE"
            else:
                pico_status = "NO MARKERS"
            last_send_time = current_time
        elif not grid_calibrated:
            pico_status = "CALIBRATING"
        
        # Draw markers on frame
        frame = draw_aruco_markers(frame, corners, ids, marker_data)
        
        # Draw red blob detection
        if blob_cx is not None:
            progress = verifier.get_progress()
            frame = draw_red_blob(frame, blob_cx, blob_cy, blob_row, blob_col, 
                                blob_verified, progress)
        
        # Highlight cells with markers
        for data in marker_data:
            if 'grid_row' in data and 'grid_col' in data and data['grid_row'] is not None and data['grid_col'] is not None:
                # Use different colors for different marker IDs
                color = (0, 255, 0) if data['id'] == 1 else (255, 0, 255)
                frame = highlight_cell(frame, data['grid_row'], data['grid_col'], GRID_SIZE, color)
        
        # Draw grid overlay
        if show_grid and v_lines is not None and h_lines is not None:
            # Draw detected grid
            frame = draw_detected_grid(frame, v_lines, h_lines)
        
        # Display calibration status
        if not grid_calibrated:
            calib_text = "Press 'm' to set manual grid"
            cv2.putText(frame, calib_text, (10, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        elif v_lines is not None:
            cv2.putText(frame, "Grid: MANUAL CALIBRATED", (10, height - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Display marker count
        marker_count_text = f"Markers: {len(marker_data)}"
        cv2.putText(frame, marker_count_text, (10, 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        # Display Pico status
        status_color = (0, 255, 0) if "ACK" in pico_status else (0, 165, 255)
        cv2.putText(frame, f"Pico: {pico_status}", (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        
        # Display detected marker IDs
        if marker_data:
            valid_markers = [m for m in marker_data if m['grid_row'] is not None and m['grid_col'] is not None]
            if valid_markers:
                ids_text = "IDs: " + ", ".join([f"{m['id']}@({m['grid_row']+1},{m['grid_col']+1})" 
                                                for m in valid_markers])
            else:
                ids_text = f"Markers: {len(marker_data)} detected (no grid)"
            cv2.putText(frame, ids_text, (10, 105), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Display workflow status
        workflow_y = 140
        if not grid_calibrated:
            workflow_text = "Status: WAITING for grid calibration"
            cv2.putText(frame, workflow_text, (10, workflow_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
        elif workflow_complete:
            workflow_text = f"Status: ALL {max_plates} PLATES COMPLETE!"
            cv2.putText(frame, workflow_text, (10, workflow_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        elif pickup_initiated:
            if blob_verified:
                workflow_text = f"Status: Plate {plates_completed}/{max_plates} - PLACED"
                workflow_color = (0, 255, 0)
            elif target_position:
                target_r, target_c = target_position
                workflow_text = f"Status: Plate {plates_completed+1}/{max_plates} - Moving to ({target_r+1},{target_c+1})"
                workflow_color = (0, 165, 255)
            else:
                workflow_text = f"Status: Plate {plates_completed+1}/{max_plates} - PICKUP Marker {active_marker_id}"
                workflow_color = (255, 165, 0)
            cv2.putText(frame, workflow_text, (10, workflow_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, workflow_color, 2)
        else:
            workflow_text = f"Status: Plate {plates_completed+1}/{max_plates} - WAITING for ArUco at (1,1)"
            cv2.putText(frame, workflow_text, (10, workflow_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        
        # Display blob verification status
        if blob_cx is not None and pickup_initiated:
            if blob_verified:
                verify_text = "VERIFIED - RELEASED"
                verify_color = (0, 255, 0)
            elif verifier.target_row is not None:
                progress = verifier.get_progress()
                verify_text = f"Verifying: {int(progress*100)}%"
                verify_color = (0, 165, 255)
            else:
                verify_text = "Blob Detected"
                verify_color = (255, 255, 0)
            
            cv2.putText(frame, verify_text, (10, workflow_y + 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, verify_color, 2)
        
        # Calculate and display FPS
        fps_frame_count += 1
        if time.time() - fps_start_time >= 1.0:
            fps_display = fps_frame_count
            fps_frame_count = 0
            fps_start_time = time.time()
        
        if SHOW_FPS:
            cv2.putText(frame, f"FPS: {fps_display}", (width - 140, 35), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # Display frame in resizable window
        cv2.namedWindow('Aruco WiFi Tracker - Forge Registry', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Aruco WiFi Tracker - Forge Registry', 800, 600)
        cv2.imshow('Aruco WiFi Tracker - Forge Registry', frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\n\nShutting down...")
            break
        elif key == ord('m'):
            MANUAL_GRID_MODE = not MANUAL_GRID_MODE
            manual_grid_corners = []
            manual_confirmed = False
            grid_calibrated = False
            v_lines = None
            h_lines = None
            print(f"\nManual grid mode: {'ON - Click 2 corners (top-left, bottom-right)' if MANUAL_GRID_MODE else 'OFF'}")
        elif key == ord('c') and MANUAL_GRID_MODE and len(manual_grid_corners) == 2:
            manual_confirmed = True
            print("\nManual grid confirmed!")
        elif key == ord('r') and MANUAL_GRID_MODE:
            manual_grid_corners = []
            manual_confirmed = False
            grid_calibrated = False
            v_lines = None
            h_lines = None
            print("\nManual grid reset - click 2 new corners")
        elif key == ord('g'):
            show_grid = not show_grid
            print(f"\nGrid overlay: {'ON' if show_grid else 'OFF'}")
        elif key == ord('s'):
            filename = f"aruco_capture_{int(time.time())}.jpg"
            cv2.imwrite(filename, frame)
            print(f"\nFrame saved as {filename}")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    if ser:
        ser.close()
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
