# Forge Registry Station - Complete Setup Guide

## Project Overview

This system implements a manual gantry control station where an agent positions metallic Aruco plates on a 5×5 grid using real-time camera feedback. The system uses:

- **Pico W**: Main controller with WiFi connectivity
- **Python Camera System**: Tracks Aruco markers and sends coordinates via WiFi
- **Manual Control**: Two potentiometers for X/Y axis control
- **Visual Feedback**: 16×2 LCD display showing current and target positions
- **Verification**: 5-second hold time requirement at target position

## Hardware Requirements

### Raspberry Pi Pico W
- 1× Raspberry Pi Pico W (with WiFi)
- USB cable for programming and power

### Motors & Motion
- 2× DC Motors (X and Y axis gantry)
- 2× Motor drivers (L298N or similar)
- 2× Limit switches (for homing X and Y axes)
- 1× Electromagnet (for picking/dropping plates)
- 1× Electromagnet driver (relay or transistor circuit)

### Input Controls
- 2× Potentiometers (10kΩ, for X and Y axis control)
- 1× Push button (with pull-up resistor)

### Display & Feedback
- 1× 16×2 LCD with I2C backpack (address 0x27 or 0x3F)
- 1× Buzzer (active or passive)
- 1× UV LED or UV light (for revealing final clue)

### Camera System
- 1× USB Webcam (overhead mount)
- PC or Raspberry Pi running Python

### Aruco Markers
- 2× Metallic Aruco plates (ID 1 and ID 2 from DICT_4X4_50)
- 5×5 grid board with UV-reactive ink clue

## Pin Configuration (Pico W)

```
PIN ASSIGNMENTS:
├─ ADC Inputs (Potentiometers)
│  ├─ GPIO 26 (ADC0) → X-axis Potentiometer
│  └─ GPIO 27 (ADC1) → Y-axis Potentiometer
│
├─ Motor Control (PWM + Direction)
│  ├─ GPIO 2 → X-axis Motor PWM
│  ├─ GPIO 3 → X-axis Motor Direction
│  ├─ GPIO 4 → Y-axis Motor PWM
│  └─ GPIO 5 → Y-axis Motor Direction
│
├─ Limit Switches (Homing)
│  ├─ GPIO 6 → X-axis Limit Switch
│  └─ GPIO 7 → Y-axis Limit Switch
│
├─ Actuators
│  ├─ GPIO 8 → Electromagnet Control
│  ├─ GPIO 10 → Buzzer
│  └─ GPIO 11 → UV LED
│
├─ User Input
│  └─ GPIO 9 → Push Button
│
└─ I2C (LCD Display)
   ├─ GPIO 0 → I2C0 SDA
   └─ GPIO 1 → I2C0 SCL
```

## Software Setup

### 1. Pico W Firmware

#### Required Configuration
Edit `EmbeddedMS3.c` line 92-93:
```c
#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"
```

#### QR Code Sequence
Edit line 118 to match your QR code (example: 5432):
```c
static int qr_sequence[4] = {5, 4, 3, 2}; // Plate 1: (5,4), Plate 2: (3,2)
```

#### Compile and Upload
```bash
# From the project directory
cd build
cmake ..
ninja
# Upload EmbeddedMS3.uf2 to Pico W in BOOTSEL mode
```

### 2. Python Camera System

#### Install Dependencies
```bash
cd Camera
pip install -r requirements.txt
# Or manually:
pip install opencv-contrib-python numpy
```

#### Configure Camera Script
Edit `aruco_wifi_tracker.py` lines 16-17:
```python
PICO_IP = "192.168.1.100"  # Set to your Pico W's IP address
PICO_PORT = 5000
```

Edit line 23 for camera selection:
```python
CAMERA_INDEX = 0  # 0=default webcam, 1=external USB camera
```

#### Run Camera Tracker
```bash
python aruco_wifi_tracker.py
```

### 3. Generate Aruco Markers

Use the provided script to generate printable markers:
```bash
cd Camera
python generate_aruco.py
```

This creates markers with IDs 1 and 2. Print them on metallic material or attach to metal plates.

## System Operation

### Stage 1: Initialization
1. Power on Pico W and start camera tracker
2. System displays "CONNECTING WIFI"
3. Once connected, displays IP address
4. System runs HOMING sequence automatically
5. LCD shows "HOMING COMPLETE. PLACE ARUCO at (1,1)"

### Stage 2: First Plate Placement
1. **Agent Action**: Scan QR code to get 4-digit sequence (e.g., 5432)
   - First pair: Target for Plate 1 → (5, 4)
   - Second pair: Target for Plate 2 → (3, 2)

2. **Agent Action**: Place either Aruco plate (ID 1 or 2) at grid position (1, 1)

3. **Agent Action**: Press push button

4. **System Response**:
   - Camera detects Aruco ID
   - LCD shows: `ID 1 DETECTED. T:(5,4). C:(1,1)`
   - Electromagnet activates (picks up plate)
   - System enters manual control mode

5. **Manual Control**:
   - Use X potentiometer to move left/right
   - Use Y potentiometer to move forward/backward
   - LCD continuously updates: `T:(5,4) C:(3,2)` showing target and current position
   - Camera tracks plate position in real-time

6. **Verification**:
   - When Current position matches Target position:
   - LCD shows: "VERIFYING... Hold position"
   - Agent must hold position for 5 consecutive seconds
   - System releases electromagnet (drops plate)
   - Buzzer confirmation beep
   - LCD: "PLACEMENT SUCCESS. ADD REMAINING ARUCO at (1,1)"

### Stage 3: Second Plate Placement
1. **Agent Action**: Place the second Aruco plate at (1, 1)
2. **Agent Action**: Press push button
3. Repeat the manual control and verification process
4. System guides to second target coordinate

### Stage 4: Completion
- Once both plates are correctly placed:
- LCD: "** SUCCESS! ** UV LIGHT ON"
- UV LED/Light activates
- Long buzzer beep (1 second)
- **Reward**: 4-digit clue revealed in UV ink on grid board

## Communication Protocol

### Python → Pico W (UDP Port 5000)
```json
{
  "timestamp": 1234567890.123,
  "markers": [
    {
      "id": 1,
      "grid_row": 2,
      "grid_col": 3,
      "center_x": 320,
      "center_y": 240,
      "area": 5000.0
    }
  ]
}
```

### Pico W → Python (Acknowledgment)
```json
{
  "state": "OK"
}
```

## State Machine Flow

```
INIT → HOMING → WAIT_PLATE_1 → PICK_PLATE_1 → MOVE_PLATE_1 → VERIFY_PLATE_1
                                                                     ↓
       COMPLETE ← VERIFY_PLATE_2 ← MOVE_PLATE_2 ← PICK_PLATE_2 ← WAIT_PLATE_2
```

## Troubleshooting

### WiFi Connection Issues
- Verify SSID and password in code
- Ensure Pico W and PC are on same network
- Check firewall settings (allow UDP port 5000)
- Use serial monitor to see Pico W's IP address

### Camera Not Detecting Markers
- Ensure proper lighting (no shadows)
- Camera must be mounted directly overhead
- Markers should be clearly visible
- Adjust `MIN_MARKER_AREA` in Python code if needed
- Verify correct ARUCO_DICT type (DICT_4X4_50)

### LCD Not Displaying
- Check I2C address (try 0x27 or 0x3F)
- Verify SDA/SCL connections
- Test with i2c_scanner example

### Motors Not Responding
- Check motor driver connections
- Verify power supply is adequate
- Test potentiometers with multimeter
- Check PWM output with oscilloscope

### Placement Verification Fails
- Ensure camera tracking is stable
- Reduce vibration in gantry system
- Adjust PLACEMENT_TIME if needed (currently 5 seconds)
- Check that grid calibration is accurate

## Calibration

### Camera Grid Calibration
1. Place markers at known grid positions
2. Verify reported coordinates match physical positions
3. Adjust camera position/angle if needed
4. Ensure entire 5×5 grid is visible in frame

### Potentiometer Deadzone
Adjust `DEADZONE` constant (line 74) if controls are too sensitive:
```c
#define DEADZONE    200  // Increase for larger deadzone
```

### Motor Speed
Adjust speed scaling in `read_pot_with_deadzone()` for finer control

## Safety Notes

- **Electromagnet**: Ensure proper driver circuit (relay/transistor with flyback diode)
- **Motor Drivers**: Use appropriate heat sinks
- **Power Supply**: Separate 5V for logic, 12V for motors (if needed)
- **UV LED**: Use appropriate current limiting resistor
- **Limit Switches**: Configure as normally-closed for safety

## Files Overview

```
EmbeddedMS3/
├── EmbeddedMS3.c           # Main Pico W firmware
├── CMakeLists.txt          # Build configuration
├── FORGE_REGISTRY_SETUP.md # This file
├── WIRING_DIAGRAM.md       # Detailed wiring guide
├── Camera/
│   ├── aruco_wifi_tracker.py    # Main camera tracking script
│   ├── generate_aruco.py        # Generate printable markers
│   └── requirements.txt         # Python dependencies
└── build/
    └── EmbeddedMS3.uf2     # Compiled firmware
```

## Support

For issues or questions:
1. Check serial monitor output from Pico W
2. Review Python console output
3. Verify all hardware connections
4. Test individual components separately

---

**Milestone 3 - Station 4: Forge Registry**
*Manual Closed-Loop Gantry Control with Real-Time Visual Feedback*
