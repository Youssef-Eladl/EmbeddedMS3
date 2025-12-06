# Forge Registry Station - Quick Start Guide

## 🚀 Quick Setup (5 Minutes)

### Step 1: Hardware Setup
1. Connect Pico W to PC via USB
2. Wire motors, potentiometers, LCD, and sensors (see WIRING_DIAGRAM.md)
3. Mount camera overhead to view entire 5×5 grid
4. Print Aruco markers (ID 1 and ID 2)

### Step 2: Configure WiFi
Edit `EmbeddedMS3.c` lines 92-93:
```c
#define WIFI_SSID           "YourWiFiName"
#define WIFI_PASSWORD       "YourPassword"
```

### Step 3: Set QR Code Sequence
Edit `EmbeddedMS3.c` line 118 with your 4-digit sequence:
```c
static int qr_sequence[4] = {5, 4, 3, 2}; // Example: QR code "5432"
```
This means: Plate 1 → (5,4), Plate 2 → (3,2)

### Step 4: Compile & Upload Firmware
```powershell
cd build
cmake ..
ninja
# Put Pico W in BOOTSEL mode (hold BOOTSEL, connect USB)
# Copy EmbeddedMS3.uf2 to RPI-RP2 drive
```

### Step 5: Setup Camera System
```powershell
cd Camera
pip install -r requirements.txt
python generate_aruco.py  # Generate markers to print
```

Edit `aruco_wifi_tracker.py` line 16:
```python
PICO_IP = "192.168.1.100"  # Get this from Pico serial output
```

### Step 6: Run System
**Terminal 1** (monitor Pico):
```powershell
# Open Serial Monitor at 115200 baud
# Note the IP address displayed
```

**Terminal 2** (run camera):
```powershell
cd Camera
python aruco_wifi_tracker.py
```

---

## 📋 Operation Checklist

### Pre-Operation
- [ ] Pico W powered and connected to WiFi
- [ ] Camera running and detecting grid
- [ ] Motors respond to potentiometers
- [ ] LCD displays "HOMING COMPLETE"
- [ ] Electromagnet tested (can pick up plate)
- [ ] Both Aruco plates ready (ID 1 and ID 2)

### First Plate (Plate 1)
1. [ ] Place either Aruco plate at grid position (1,1)
2. [ ] Press push button
3. [ ] LCD shows detected ID and target coordinates
4. [ ] Electromagnet activates (picks up plate)
5. [ ] Use potentiometers to move gantry
6. [ ] Watch LCD for current position
7. [ ] Align current position with target
8. [ ] Hold position steady for 5 seconds
9. [ ] Electromagnet releases, buzzer beeps

### Second Plate (Plate 2)
10. [ ] Place remaining Aruco plate at (1,1)
11. [ ] Press push button
12. [ ] Repeat alignment process
13. [ ] Hold for 5 seconds
14. [ ] Success: UV light turns on!

### Collect Reward
15. [ ] Read 4-digit clue under UV light on grid board
16. [ ] Record clue for next station

---

## 🎮 Control Guide

### Potentiometer Control
- **Left Pot (X-axis)**: Left/Right movement
  - Turn CCW → Move Left
  - Center → Stop
  - Turn CW → Move Right

- **Right Pot (Y-axis)**: Forward/Backward movement
  - Turn CCW → Move Backward
  - Center → Stop
  - Turn CW → Move Forward

### LCD Display Meanings
```
"HOMING..."                  → System finding origin
"PLACE ARUCO at (1,1)"      → Ready for plate
"ID 1 DETECTED"             → Camera identified plate
"T:(5,4) C:(2,3)"          → Target vs Current position
"VERIFYING..."              → Hold position!
"PLACEMENT SUCCESS"         → Plate placed correctly
"** SUCCESS! **"            → Both plates complete
```

### Status Indicators
- **Buzzer Short Beep**: Plate picked up
- **Buzzer Long Beep**: Placement verified
- **Buzzer 1-sec Beep**: Mission complete
- **UV LED On**: Clue revealed

---

## 🔧 Common Issues & Fixes

### Issue: WiFi Won't Connect
**Solution:**
- Check SSID/password in code
- Verify 2.4GHz network (Pico W doesn't support 5GHz)
- Serial monitor shows connection attempts

### Issue: Camera Not Detecting Markers
**Solution:**
- Improve lighting (bright, even)
- Move camera closer/farther
- Ensure markers are flat and visible
- Check marker size (should be 5-10cm)

### Issue: Position Not Updating
**Solution:**
- Verify camera tracking window shows marker
- Check WiFi connection (green status in Python window)
- Serial monitor should show "Received marker" messages

### Issue: Motors Don't Respond to Pots
**Solution:**
- Test pots with multimeter (should read 0-10kΩ)
- Check ADC connections (GPIO 26, 27)
- Verify motor driver power supply
- Serial monitor to check ADC readings

### Issue: Can't Hold Position for 5 Seconds
**Solution:**
- Reduce gantry vibration
- Calibrate camera grid alignment
- Practice smooth potentiometer control
- Check if camera tracking is stable

### Issue: Electromagnet Won't Pick Up Plate
**Solution:**
- Verify 12V supply to electromagnet
- Check relay/transistor is switching
- Test with GPIO 8 directly (measure voltage)
- Ensure plates are ferromagnetic (iron, steel, nickel)

---

## 📊 System Status Indicators

### Python Camera Window
```
Markers: 1               → Number detected
Pico: ACK: OK           → Communication working
IDs: 1@(2,3)            → Marker 1 at row 2, col 3
FPS: 30                 → Frame rate
```

### Serial Monitor (Pico W)
```
WiFi connected!         → Network ready
IP: 192.168.1.100      → Use this in Python
Received marker: ID=1   → Getting camera data
Grid Position: (2,3)    → Current position
```

---

## 🎯 Success Criteria

✅ **Station Complete When:**
1. Both Aruco plates placed at correct coordinates
2. UV LED illuminated
3. 4-digit clue visible under UV light
4. LCD shows "** SUCCESS! **"

⏱️ **Expected Time:** 5-10 minutes per attempt

---

## 📞 Debug Commands

### Check WiFi IP
```powershell
# Serial monitor will display IP on startup
# Or use Pico W with LED blink code to indicate IP
```

### Test Camera
```powershell
python aruco_wifi_tracker.py
# Press 's' to save frame
# Press 'g' to toggle grid
# Press 'q' to quit
```

### Test Motors Individually
```c
// Add to main loop for testing:
motor_set(MOTOR_X_PWM, MOTOR_X_DIR, 100);  // X forward
sleep_ms(2000);
motors_stop();
```

### Test LCD
```c
// Add to main for testing:
lcd_clear();
lcd_printf(0, 0, "Test Line 1");
lcd_printf(0, 1, "Test Line 2");
```

---

## 📚 Additional Documentation

- **FORGE_REGISTRY_SETUP.md** - Complete hardware and software setup
- **WIRING_DIAGRAM.md** - Detailed pin connections
- **Camera/CAMERA_README.md** - Camera system configuration

---

## 🎓 Tips for Success

1. **Calibrate First**: Test each component individually before full system
2. **Lighting Matters**: Good lighting = reliable tracking
3. **Smooth Control**: Practice gentle potentiometer movements
4. **Stay Steady**: During verification, minimize vibration
5. **Plan Moves**: Think about path before moving gantry

**Good luck, Agent! The Forge awaits your precision. 🔥**
