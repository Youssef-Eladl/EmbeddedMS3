# Forge Registry Station - Milestone 3, Station 4

## 🎯 Mission Objective

Position two metallic Aruco plates on a 5×5 grid using manual gantry control with real-time camera feedback. Successfully place both plates at coordinates specified by a QR code clue to reveal a UV-ink reward code.

## 🔥 System Overview

This is a **manual closed-loop control system** where:
- **Agent** manually controls X/Y gantry using potentiometers
- **Camera** tracks Aruco markers in real-time via WiFi
- **Pico W** displays current vs target positions on LCD
- **Success** requires 5-second hold at target position

### Key Features
- ✅ Real-time WiFi communication (Python → Pico W)
- ✅ Dual Aruco marker tracking (ID 1 and ID 2)
- ✅ Manual potentiometer-based motion control
- ✅ 16×2 LCD real-time position display
- ✅ 5-second placement verification
- ✅ Electromagnet pickup/release system
- ✅ Automatic homing sequence
- ✅ UV light reward activation

## 📦 What's Included

```
EmbeddedMS3/
├── 📄 README.md                    ← You are here
├── 📄 QUICKSTART.md                ← 5-minute setup guide
├── 📄 FORGE_REGISTRY_SETUP.md      ← Complete documentation
├── 📄 WIRING_DIAGRAM.md            ← Pin connections
│
├── 💻 EmbeddedMS3.c                ← Pico W firmware (main code)
├── 📋 CMakeLists.txt               ← Build configuration
│
├── Camera/
│   ├── 🎥 aruco_wifi_tracker.py   ← Main camera tracker (USE THIS)
│   ├── 🧪 test_system.py          ← System test script
│   ├── 🎨 generate_aruco.py       ← Generate printable markers
│   ├── ⚙️  config_forge_registry.py ← Configuration reference
│   ├── 📋 requirements.txt         ← Python dependencies
│   ├── 📖 CAMERA_README.md         ← Camera system guide
│   └── ... (legacy scripts)
│
└── build/
    └── EmbeddedMS3.uf2             ← Compiled firmware (after build)
```

## 🚀 Quick Start (Choose Your Path)

### 🏃 Super Quick (Experienced Users)
```bash
# 1. Edit WiFi credentials in EmbeddedMS3.c lines 92-93
# 2. Edit QR sequence in EmbeddedMS3.c line 118
# 3. Build and flash
cd build && cmake .. && ninja
# Flash EmbeddedMS3.uf2 to Pico W

# 4. Setup Python
cd ../Camera
pip install -r requirements.txt
python generate_aruco.py

# 5. Edit PICO_IP in aruco_wifi_tracker.py line 16
# 6. Run tracker
python aruco_wifi_tracker.py
```

### 📚 Detailed Guide (First Time Setup)
See **[QUICKSTART.md](QUICKSTART.md)** for step-by-step instructions

### 🔧 Full Documentation (Hardware Setup)
See **[FORGE_REGISTRY_SETUP.md](FORGE_REGISTRY_SETUP.md)** for complete guide

## 🔌 Hardware Requirements

### Essential Components
- 1× Raspberry Pi Pico W (with WiFi)
- 2× DC Motors with drivers (L298N or similar)
- 2× Potentiometers (10kΩ)
- 1× Electromagnet with driver
- 1× 16×2 LCD with I2C backpack
- 2× Limit switches
- 1× Push button
- 1× Buzzer
- 1× UV LED/Light
- 1× USB Webcam (overhead mount)
- 2× Aruco markers (ID 1 and 2)
- 5×5 grid board with UV-reactive ink

### Power Requirements
- 12V DC (2A) - Motors and electromagnet
- 5V DC (2A) - Pico W and logic

See **[WIRING_DIAGRAM.md](WIRING_DIAGRAM.md)** for complete pin connections

## 🎮 Operation Flow

```
1. INITIALIZATION
   └─→ Pico W connects to WiFi
   └─→ Camera tracker starts
   └─→ System runs homing sequence

2. FIRST PLATE (ID 1 or 2)
   └─→ Place Aruco at (1,1)
   └─→ Press button → Electromagnet picks up
   └─→ Use pots to move to target
   └─→ LCD shows: T:(5,4) C:(2,3)
   └─→ Hold position for 5 seconds
   └─→ Electromagnet releases → Buzzer beeps

3. SECOND PLATE
   └─→ Place remaining Aruco at (1,1)
   └─→ Repeat process for second target

4. SUCCESS!
   └─→ UV LED activates
   └─→ Read 4-digit clue under UV light
```

## 🧪 Testing Your Setup

Run the system test before operation:
```bash
cd Camera
python test_system.py
```

This checks:
- ✓ Camera detection
- ✓ Aruco dictionary
- ✓ UDP socket
- ✓ Network connectivity
- ✓ Full marker detection

## 📡 Communication Protocol

**Python → Pico W (UDP Port 5000)**
```json
{
  "timestamp": 1234567890.123,
  "markers": [{
    "id": 1,
    "grid_row": 2,
    "grid_col": 3,
    "center_x": 320,
    "center_y": 240
  }]
}
```

**Pico W → Python (Acknowledgment)**
```json
{"state": "OK"}
```

## ⚙️ Configuration

### Edit WiFi (Required)
`EmbeddedMS3.c` lines 92-93:
```c
#define WIFI_SSID           "YourWiFiName"
#define WIFI_PASSWORD       "YourPassword"
```

### Edit QR Code Sequence (Required)
`EmbeddedMS3.c` line 118:
```c
// Example: QR code "5432" → Plate 1:(5,4), Plate 2:(3,2)
static int qr_sequence[4] = {5, 4, 3, 2};
```

### Edit Pico IP (Required)
`Camera/aruco_wifi_tracker.py` line 16:
```python
PICO_IP = "192.168.1.100"  # Get from serial monitor
```

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| **WiFi won't connect** | Verify 2.4GHz network, check credentials |
| **Camera not detecting** | Improve lighting, check marker size |
| **Position not updating** | Check WiFi connection, verify PICO_IP |
| **Motors don't respond** | Test pots with multimeter, check motor drivers |
| **Can't hold 5 seconds** | Reduce vibration, practice smooth control |
| **LCD shows garbage** | Check I2C address (0x27 or 0x3F) |

See **[FORGE_REGISTRY_SETUP.md](FORGE_REGISTRY_SETUP.md)** for detailed troubleshooting

## 📊 System Specifications

| Parameter | Value |
|-----------|-------|
| Grid Size | 5×5 cells |
| Camera Resolution | 640×480 @ 30fps |
| Update Rate | 10 Hz (100ms intervals) |
| Verification Time | 5 seconds |
| Coordinate System | 0-indexed (internal), 1-indexed (display) |
| Communication | UDP over WiFi |
| Aruco Dictionary | DICT_4X4_50 |

## 🎓 Learning Objectives

This project demonstrates:
- ✅ **Manual Closed-Loop Control** - Human-in-the-loop positioning
- ✅ **Real-Time Computer Vision** - Aruco marker tracking
- ✅ **Wireless Communication** - UDP over WiFi
- ✅ **State Machine Design** - Multi-stage workflow
- ✅ **Sensor Fusion** - Camera + potentiometers
- ✅ **Embedded Systems** - Pico W programming
- ✅ **Human-Machine Interface** - LCD feedback + manual control

## 📁 File Reference

### Core Files
- **EmbeddedMS3.c** - Main Pico W firmware with WiFi, motors, LCD, state machine
- **aruco_wifi_tracker.py** - Camera tracking with WiFi communication
- **CMakeLists.txt** - Build configuration with required libraries

### Documentation
- **README.md** - This file (project overview)
- **QUICKSTART.md** - Fast setup guide
- **FORGE_REGISTRY_SETUP.md** - Complete documentation
- **WIRING_DIAGRAM.md** - Detailed pin connections
- **Camera/CAMERA_README.md** - Camera system guide

### Utilities
- **test_system.py** - Component testing
- **generate_aruco.py** - Create printable markers
- **config_forge_registry.py** - Configuration reference

## 🆘 Support & Resources

### Build Issues
```bash
# Clean rebuild
cd build
rm -rf *
cmake ..
ninja
```

### Camera Issues
```bash
# Test camera
python test_system.py

# Generate fresh markers
python generate_aruco.py
```

### Serial Monitoring (115200 baud)
- Shows WiFi connection status
- Displays assigned IP address
- Reports marker detection
- Shows state transitions

## 🏆 Success Criteria

✅ **Station Complete:**
- Both Aruco plates at correct coordinates
- UV LED illuminated
- 4-digit clue visible under UV light
- LCD displays "** SUCCESS! **"

⏱️ **Expected Time:** 5-10 minutes per attempt

## 🎯 Next Steps

1. **First Time Setup:**
   - Read [QUICKSTART.md](QUICKSTART.md)
   - Wire hardware per [WIRING_DIAGRAM.md](WIRING_DIAGRAM.md)
   - Run system test: `python test_system.py`

2. **Configure System:**
   - Set WiFi credentials
   - Set QR code sequence
   - Update Pico IP in Python

3. **Test & Calibrate:**
   - Verify each component
   - Test manual motor control
   - Calibrate camera view

4. **Operation:**
   - Run homing sequence
   - Place first plate
   - Manual positioning
   - Repeat for second plate
   - Collect reward!

## 📝 Notes

- **WiFi**: Pico W only supports 2.4GHz networks
- **Camera**: Must be mounted overhead with full grid view
- **Markers**: Print on A4 paper or attach to metal plates
- **Lighting**: Bright, even lighting crucial for tracking
- **Control**: Practice smooth potentiometer movements

## 📜 License & Credits

**Project:** Forge Registry Station - Milestone 3, Station 4  
**Platform:** Raspberry Pi Pico W  
**Date:** December 2025  
**Author:** GitHub Copilot  

---

**🔥 The Forge awaits your precision, Agent. Good luck! 🔥**

For detailed setup: **[FORGE_REGISTRY_SETUP.md](FORGE_REGISTRY_SETUP.md)**  
For quick start: **[QUICKSTART.md](QUICKSTART.md)**  
For wiring: **[WIRING_DIAGRAM.md](WIRING_DIAGRAM.md)**
