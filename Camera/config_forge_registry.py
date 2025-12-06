"""
Configuration file for Forge Registry Station
Copy this to config.py and edit with your settings
"""

# ============================================================================
# WIFI CONFIGURATION
# ============================================================================

# Pico W WiFi Settings (edit in EmbeddedMS3.c)
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# Network Settings (edit in aruco_wifi_tracker.py)
PICO_IP = "192.168.1.100"  # Get from Pico serial monitor after WiFi connects
PICO_UDP_PORT = 5000
LOCAL_UDP_PORT = 5001

# ============================================================================
# QR CODE SEQUENCE
# ============================================================================

# The 4-digit sequence from QR code determines target coordinates
# Example: QR code shows "5432"
# This means: Plate 1 target = (5,4), Plate 2 target = (3,2)

QR_SEQUENCE = [5, 4, 3, 2]  # Edit in EmbeddedMS3.c line 118

# ============================================================================
# CAMERA SETTINGS
# ============================================================================

CAMERA_INDEX = 0  # 0 = default webcam, 1 = external USB camera, 2 = second external
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# ============================================================================
# ARUCO DETECTION SETTINGS
# ============================================================================

# Aruco Dictionary Type
# Options: DICT_4X4_50, DICT_5X5_100, DICT_6X6_250
ARUCO_DICT = "DICT_4X4_50"

# Minimum marker area in pixels (adjust if markers not detected)
MIN_MARKER_AREA = 1000

# Grid size (5x5 for this project)
GRID_SIZE = 5

# ============================================================================
# HARDWARE CALIBRATION
# ============================================================================

# Potentiometer Deadzone (0-4095)
# Increase if motors jitter when pots are centered
POT_DEADZONE = 200

# Placement verification time (milliseconds)
# Time marker must stay at target position
PLACEMENT_HOLD_TIME = 5000  # 5 seconds

# Motor PWM maximum (16-bit: 0-65535)
PWM_MAX = 65535

# ============================================================================
# PIN ASSIGNMENTS (for reference - edit in EmbeddedMS3.c)
# ============================================================================

PINS = {
    'POT_X': 26,        # ADC0 - X-axis potentiometer
    'POT_Y': 27,        # ADC1 - Y-axis potentiometer
    'MOTOR_X_PWM': 2,   # X-axis motor PWM
    'MOTOR_X_DIR': 3,   # X-axis motor direction
    'MOTOR_Y_PWM': 4,   # Y-axis motor PWM
    'MOTOR_Y_DIR': 5,   # Y-axis motor direction
    'LIMIT_X': 6,       # X-axis limit switch
    'LIMIT_Y': 7,       # Y-axis limit switch
    'MAGNET': 8,        # Electromagnet control
    'BUTTON': 9,        # Push button
    'BUZZER': 10,       # Buzzer
    'UV_LED': 11,       # UV LED/Light
    'I2C_SDA': 0,       # I2C SDA (LCD)
    'I2C_SCL': 1,       # I2C SCL (LCD)
}

# LCD I2C Address (common values: 0x27 or 0x3F)
LCD_I2C_ADDRESS = 0x27

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

SHOW_GRID_OVERLAY = True
SHOW_FPS = True
SHOW_DEBUG_INFO = True

# Update rates
CAMERA_SEND_INTERVAL = 0.1  # Send updates every 100ms (10 Hz)
LCD_UPDATE_INTERVAL = 200   # Update LCD every 200ms

# ============================================================================
# TESTING/DEBUG SETTINGS
# ============================================================================

DEBUG_MODE = False
VERBOSE_SERIAL = True
SAVE_FRAMES = False  # Auto-save frames during operation

# ============================================================================
# USAGE NOTES
# ============================================================================

"""
1. WIFI SETUP:
   - Edit WIFI_SSID and WIFI_PASSWORD in EmbeddedMS3.c
   - Flash firmware to Pico W
   - Read IP address from serial monitor
   - Update PICO_IP in aruco_wifi_tracker.py

2. QR CODE:
   - Scan QR code to get 4-digit sequence
   - Update QR_SEQUENCE in EmbeddedMS3.c
   - Recompile and upload

3. CAMERA SETUP:
   - Mount camera overhead
   - Ensure entire 5x5 grid visible
   - Run: python aruco_wifi_tracker.py
   - Press 'g' to toggle grid overlay

4. CALIBRATION:
   - Adjust MIN_MARKER_AREA if markers not detected
   - Adjust POT_DEADZONE if motors jitter
   - Check LCD_I2C_ADDRESS if LCD shows garbage

5. OPERATION:
   - Place Aruco plate at (1,1)
   - Press button
   - Use pots to move to target
   - Hold for 5 seconds
   - Repeat for second plate
"""
