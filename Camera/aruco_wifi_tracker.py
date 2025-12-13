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

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# Serial Configuration
SERIAL_PORT = "COM5"      # Change to the Pico's COM port (e.g., COM5 on Windows, /dev/ttyACM0 on Linux)
SERIAL_BAUD = 115200
SERIAL_TIMEOUT = 0.01      # Seconds

# Grid Configuration
GRID_SIZE = 5  # 5x5 grid

# Camera Configuration
CAMERA_INDEX = 0  # 0 for default webcam, 1 for external camera
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# ArUco Configuration
ARUCO_DICT = cv2.aruco.DICT_4X4_50  # ArUco dictionary type
MIN_MARKER_AREA = 1000  # Minimum marker area in pixels

# Display Configuration
SHOW_GRID_OVERLAY = True
SHOW_FPS = True
SEND_INTERVAL = 0.1  # Send updates every 100ms (10Hz)

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
            cv2.putText(frame, label, (x - 30, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
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
            font_scale = 0.7
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
            if 'grid_row' in data and 'grid_col' in data:
                grid_text = f"({data['grid_row']+1},{data['grid_col']+1})"
                cv2.putText(frame, grid_text, 
                           (center_x - 25, center_y + 25),
                           font, 0.5, (255, 255, 0), 1)
    
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
    """Send the first detected marker as CSV: id,row,col\n"""
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

# ============================================================================
# MAIN TRACKING LOOP
# ============================================================================

def main():
    """Main function to run the Aruco tracking system"""
    
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
    print("=" * 70)
    
    # Initialize serial
    port, available = pick_serial_port(SERIAL_PORT)
    if port is None:
        print("No serial ports found. Plug in the Pico and try again.")
        return
    if port != SERIAL_PORT:
        print(f"Using detected port: {port} (preferred {SERIAL_PORT}). Available: {available}")
    ser = open_serial(port, SERIAL_BAUD)
    if ser is None:
        print("Failed to open serial port. Exiting...")
        return
    
    # Initialize webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
    
    if not cap.isOpened():
        print("ERROR: Cannot access camera!")
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
    
    while True:
        # Capture frame
        ret, frame = cap.read()
        
        if not ret:
            print("ERROR: Failed to capture frame!")
            break
        
        height, width = frame.shape[:2]
        
        # Detect ArUco markers
        corners, ids, marker_data = detect_aruco_markers(frame, ARUCO_DICT)
        
        # Add grid coordinates to marker data
        for data in marker_data:
            row, col = pixel_to_grid(data['center_x'], data['center_y'], width, height, GRID_SIZE)
            data['grid_row'] = row
            data['grid_col'] = col
        
        # Send data to Pico at specified interval
        current_time = time.time()
        if current_time - last_send_time >= SEND_INTERVAL:
            if marker_data:
                success = send_marker_data(ser, marker_data)
                pico_status = "SENT" if success else "FAILED"
            else:
                pico_status = "NO MARKERS"
            last_send_time = current_time
        
        # Draw markers on frame
        frame = draw_aruco_markers(frame, corners, ids, marker_data)
        
        # Highlight cells with markers
        for data in marker_data:
            if 'grid_row' in data and 'grid_col' in data:
                # Use different colors for different marker IDs
                color = (0, 255, 0) if data['id'] == 1 else (255, 0, 255)
                frame = highlight_cell(frame, data['grid_row'], data['grid_col'], GRID_SIZE, color)
        
        # Draw grid overlay
        if show_grid:
            frame = draw_grid_overlay(frame, GRID_SIZE)
        
        # Display marker count
        marker_count_text = f"Markers: {len(marker_data)}"
        cv2.putText(frame, marker_count_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Display Pico status
        status_color = (0, 255, 0) if "ACK" in pico_status else (0, 165, 255)
        cv2.putText(frame, f"Pico: {pico_status}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        # Display detected marker IDs
        if marker_data:
            ids_text = "IDs: " + ", ".join([f"{m['id']}@({m['grid_row']+1},{m['grid_col']+1})" 
                                            for m in marker_data])
            cv2.putText(frame, ids_text, (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
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
        cv2.imshow('Aruco WiFi Tracker - Forge Registry', frame)
        
        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\n\nShutting down...")
            break
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
