"""
Serial Communication Module for Grid Tracking System
Sends grid coordinates to Arduino/ESP32 via Serial port
Author: GitHub Copilot
Date: November 2025

Compatible with: Arduino Uno, Mega, Nano, ESP32, ESP8266, Raspberry Pi Pico
"""

import cv2
import numpy as np
import time
import serial
import serial.tools.list_ports

# ============================================================================
# CONFIGURATION
# ============================================================================

# Serial Configuration
SERIAL_PORT = 'COM3'  # Change to your port (COM3, COM4 on Windows, /dev/ttyUSB0 on Linux)
BAUD_RATE = 9600      # Must match Arduino code
SERIAL_TIMEOUT = 1    # Seconds

# Tracking Configuration (same as main script)
LOWER_HSV = np.array([0, 120, 70])
UPPER_HSV = np.array([10, 255, 255])
LOWER_HSV_ALT = np.array([170, 120, 70])
UPPER_HSV_ALT = np.array([180, 255, 255])

GRID_SIZE = 5
MIN_OBJECT_AREA = 100
CAMERA_INDEX = 0

# ============================================================================
# SERIAL COMMUNICATION FUNCTIONS
# ============================================================================

def list_available_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    available_ports = []
    
    print("\nAvailable Serial Ports:")
    print("-" * 60)
    
    if not ports:
        print("No serial ports found!")
        return available_ports
    
    for port in ports:
        print(f"  {port.device} - {port.description}")
        available_ports.append(port.device)
    
    print("-" * 60)
    return available_ports

def connect_serial(port, baud_rate):
    """Connect to serial port"""
    try:
        ser = serial.Serial(port, baud_rate, timeout=SERIAL_TIMEOUT)
        time.sleep(2)  # Wait for Arduino to reset
        print(f"Connected to {port} at {baud_rate} baud")
        return ser
    except serial.SerialException as e:
        print(f"ERROR: Could not connect to {port}")
        print(f"Details: {e}")
        return None

def send_coordinates(ser, row, col):
    """
    Send grid coordinates to microcontroller
    Format: "ROW,COL\n" (e.g., "2,4\n")
    """
    if ser is None or not ser.is_open:
        return False
    
    try:
        message = f"{row},{col}\n"
        ser.write(message.encode())
        return True
    except serial.SerialException as e:
        print(f"\nERROR sending data: {e}")
        return False

def read_serial_response(ser):
    """Read response from microcontroller (if any)"""
    if ser is None or not ser.is_open:
        return None
    
    try:
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            return response
    except:
        return None
    
    return None

# ============================================================================
# DETECTION FUNCTIONS (copied from main script)
# ============================================================================

def detect_object(frame, lower_hsv, upper_hsv, lower_hsv_alt=None, upper_hsv_alt=None):
    """Detect colored object in frame"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
    
    if lower_hsv_alt is not None and upper_hsv_alt is not None:
        mask_alt = cv2.inRange(hsv, lower_hsv_alt, upper_hsv_alt)
        mask = cv2.bitwise_or(mask, mask_alt)
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        return None, None, 0
    
    largest_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_contour)
    
    if area < MIN_OBJECT_AREA:
        return None, None, 0
    
    M = cv2.moments(largest_contour)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return cx, cy, area
    
    return None, None, 0

def pixel_to_grid(cx, cy, frame_width, frame_height, grid_size=5):
    """Convert pixel coordinates to grid coordinates"""
    col = int(cx / (frame_width / grid_size))
    row = int(cy / (frame_height / grid_size))
    col = max(0, min(col, grid_size - 1))
    row = max(0, min(row, grid_size - 1))
    return row, col

def draw_grid_overlay(frame, grid_size=5):
    """Draw grid overlay"""
    height, width = frame.shape[:2]
    cell_width = width // grid_size
    cell_height = height // grid_size
    
    for i in range(1, grid_size):
        x = i * cell_width
        cv2.line(frame, (x, 0), (x, height), (255, 255, 255), 2)
    
    for i in range(1, grid_size):
        y = i * cell_height
        cv2.line(frame, (0, y), (width, y), (255, 255, 255), 2)
    
    return frame

# ============================================================================
# MAIN FUNCTION WITH SERIAL COMMUNICATION
# ============================================================================

def main():
    """Main tracking function with serial output"""
    
    print("=" * 60)
    print("GRID TRACKER WITH SERIAL COMMUNICATION")
    print("=" * 60)
    
    # List available ports
    available_ports = list_available_ports()
    
    # Connect to serial port
    print(f"\nAttempting to connect to {SERIAL_PORT}...")
    ser = connect_serial(SERIAL_PORT, BAUD_RATE)
    
    if ser is None:
        print("\nWARNING: Running without serial connection")
        print("Fix the port and restart, or continue without serial output")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    else:
        print("Serial connection established!")
    
    # Initialize camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print("ERROR: Cannot access camera!")
        if ser:
            ser.close()
        return
    
    print("\nCamera initialized!")
    print("\nControls:")
    print("  'q' - Quit")
    print("  's' - Toggle serial transmission")
    print("=" * 60)
    
    # State variables
    prev_row, prev_col = None, None
    serial_enabled = (ser is not None)
    last_send_time = 0
    send_interval = 0.1  # Send every 100ms to avoid flooding
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("ERROR: Failed to capture frame!")
            break
        
        height, width = frame.shape[:2]
        
        # Detect object
        cx, cy, area = detect_object(frame, LOWER_HSV, UPPER_HSV, 
                                     LOWER_HSV_ALT, UPPER_HSV_ALT)
        
        if cx is not None and cy is not None:
            row, col = pixel_to_grid(cx, cy, width, height, GRID_SIZE)
            
            # Send to serial if enabled and position changed
            if serial_enabled and ser and (row != prev_row or col != prev_col):
                current_time = time.time()
                if current_time - last_send_time >= send_interval:
                    if send_coordinates(ser, row, col):
                        last_send_time = current_time
                        
                        # Check for response
                        response = read_serial_response(ser)
                        if response:
                            print(f"\nArduino says: {response}")
            
            prev_row, prev_col = row, col
            
            # Draw detection
            cv2.circle(frame, (cx, cy), 10, (0, 0, 255), -1)
            cv2.circle(frame, (cx, cy), 15, (255, 255, 255), 2)
            
            # Display info
            coord_text = f"Position: ({row}, {col})"
            cv2.putText(frame, coord_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            serial_status = "Serial: ON" if serial_enabled else "Serial: OFF"
            color = (0, 255, 0) if serial_enabled else (0, 0, 255)
            cv2.putText(frame, serial_status, (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            print(f"Position: ({row}, {col}) | Serial: {'SENT' if serial_enabled else 'OFF'}", end='\r')
        
        else:
            cv2.putText(frame, "No object detected", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Draw grid
        frame = draw_grid_overlay(frame, GRID_SIZE)
        
        # Display
        cv2.imshow('Grid Tracker with Serial', frame)
        
        # Handle keys
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            print("\n\nShutting down...")
            break
        elif key == ord('s'):
            if ser:
                serial_enabled = not serial_enabled
                print(f"\nSerial transmission: {'ENABLED' if serial_enabled else 'DISABLED'}")
            else:
                print("\nSerial not connected!")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    if ser:
        ser.close()
        print("Serial connection closed.")
    print("Application closed.")

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
