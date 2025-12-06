# Troubleshooting Guide - Grid Object Tracking System

## 🔍 Systematic Problem Solving

Use this guide to diagnose and fix common issues step-by-step.

---

## 🚦 Start Here: Initial Diagnosis

### Question 1: Can you run Python scripts?

**Test:**
```powershell
python --version
```

**If it fails:**
- ❌ Python not installed → Install Python 3.8+ from python.org
- ❌ Command not found → Add Python to PATH
- ❌ Wrong version → Upgrade Python

**If it works:** → Go to Question 2

---

### Question 2: Are packages installed?

**Test:**
```powershell
python -c "import cv2, numpy; print('Success')"
```

**If it fails:**
```powershell
pip install opencv-python numpy pyserial
```

**If it still fails:**
- Try: `python -m pip install opencv-python numpy`
- Or: `pip install --user opencv-python numpy`

**If it works:** → Go to Question 3

---

### Question 3: Does the camera open?

**Test:**
```powershell
python -c "import cv2; cap=cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAILED'); cap.release()"
```

**If FAILED:**

1. Try different indices:
```python
# In OpenCV.py line 31
CAMERA_INDEX = 1  # Try 0, 1, 2
```

2. Check if camera is in use:
   - Close other apps (Zoom, Teams, Skype)
   - Close other Python scripts

3. Check permissions:
   - Windows: Settings → Privacy → Camera → Allow apps
   - Check antivirus blocking camera

**If OK:** → Go to Question 4

---

### Question 4: Does the script run without errors?

**Test:**
```powershell
python OpenCV.py
```

**If it crashes:**

1. Read the error message carefully
2. Common errors:
   - `ImportError`: Package not installed
   - `VideoCapture Error`: Camera issue
   - `Permission denied`: File access issue

**If it runs:** → Go to Question 5

---

### Question 5: Do you see a video window?

**If NO window appears:**
- Window might be off-screen → Alt+Tab to find it
- Running in virtual environment without display
- Try pressing Alt+Space → Move

**If YES but black screen:**
- Camera might be covered
- Wrong CAMERA_INDEX
- Camera hardware issue

**If YES with video:** → Go to Question 6

---

### Question 6: Is the object detected?

**Look for:** Red circle on object, green text "Position: (x, y)"

**If NO:**

### 🎨 Color Calibration Issues

#### Problem: Object not detected at all

**Solution A: Run Calibration Tool**
```powershell
python hsv_calibration.py
```

Steps:
1. Place object in view
2. Adjust trackbars until object is WHITE in mask window
3. Everything else should be BLACK
4. Press 's' to save
5. Copy values to OpenCV.py lines 17-23

**Solution B: Use Preset Values**

For **RED** object:
```python
LOWER_HSV = np.array([0, 120, 70])
UPPER_HSV = np.array([10, 255, 255])
LOWER_HSV_ALT = np.array([170, 120, 70])
UPPER_HSV_ALT = np.array([180, 255, 255])
```

For **GREEN** object:
```python
LOWER_HSV = np.array([40, 40, 40])
UPPER_HSV = np.array([80, 255, 255])
LOWER_HSV_ALT = None
UPPER_HSV_ALT = None
```

For **BLUE** object:
```python
LOWER_HSV = np.array([100, 100, 100])
UPPER_HSV = np.array([130, 255, 255])
LOWER_HSV_ALT = None
UPPER_HSV_ALT = None
```

**Solution C: Improve Conditions**
- Add more lighting
- Remove shadows
- Use more contrasting color
- Ensure object is solid color (no patterns)

**Solution D: Lower Threshold**
```python
# In OpenCV.py line 28
MIN_OBJECT_AREA = 50  # Lower to detect smaller objects
```

**If DETECTED:** → Go to Question 7

---

### Question 7: Are coordinates correct?

**Check:** Does the displayed position match physical location?

**If NO:**

### 📐 Grid Alignment Issues

#### Problem: Coordinates are wrong or inconsistent

**Solution A: Check Grid Visibility**
1. Ensure ENTIRE grid is visible in camera view
2. No corners cut off
3. Grid should fill most of the frame

**Solution B: Level Camera**
1. Camera must be parallel to grid (top-down view)
2. Use level or angle measurement
3. Adjust camera position/angle

**Solution C: Verify Grid Size**
1. Ensure grid is exactly 5×5 cells
2. Each cell must be equal size
3. Measure with ruler

**Solution D: Toggle Grid Overlay**
1. Press 'g' to show grid overlay
2. Overlay should align with physical grid
3. If not aligned → adjust camera

**If coordinates correct:** → Success! 🎉

---

## 🐛 Specific Error Messages

### ImportError: No module named 'cv2'
```powershell
pip install opencv-python
```

### ImportError: No module named 'numpy'
```powershell
pip install numpy
```

### ImportError: No module named 'serial'
```powershell
pip install pyserial
```

### "Camera index 0 failed"
Try CAMERA_INDEX = 1 or 2

### "Permission denied" (camera)
- Windows: Settings → Privacy → Camera
- Check antivirus settings

### "Port already in use" (serial)
- Close Arduino IDE Serial Monitor
- Close other Python scripts
- Disconnect and reconnect device

---

## ⚠️ Common Problems Deep-Dive

### Problem: Object flickers in/out of detection

**Causes:**
1. Object near HSV threshold boundary
2. Lighting inconsistency
3. Object too small

**Solutions:**
1. Widen HSV range slightly
2. Improve lighting (diffused, even)
3. Use larger object
4. Increase MIN_OBJECT_AREA to filter noise

**Test:**
```python
# Widen saturation range
LOWER_HSV = np.array([0, 100, 50])  # Lower S and V minimums
```

---

### Problem: Wrong objects detected

**Causes:**
1. Background objects have similar color
2. HSV range too wide
3. Shadows or reflections

**Solutions:**
1. Remove background objects
2. Narrow HSV range (use calibration tool)
3. Increase MIN_OBJECT_AREA
4. Improve lighting

**Test:**
```python
# More specific saturation/value
LOWER_HSV = np.array([0, 150, 100])  # Higher minimums
```

---

### Problem: Coordinates jump between cells

**Causes:**
1. Object on cell boundary
2. Detection centroid unstable
3. Small detection area

**Solutions:**
1. Ensure object fully in cell
2. Use larger, solid-color object
3. Add smoothing (moving average)

**Code to add smoothing:**
```python
# Add after line 238 in OpenCV.py
if prev_row is not None:
    row = int(0.7 * row + 0.3 * prev_row)
    col = int(0.7 * col + 0.3 * prev_col)
```

---

### Problem: Low FPS (slow performance)

**Causes:**
1. Resolution too high
2. Other apps using resources
3. Slow computer
4. Complex morphology

**Solutions:**

**Solution 1: Reduce Resolution**
```python
# In OpenCV.py lines 32-33
FRAME_WIDTH = 480   # Instead of 640
FRAME_HEIGHT = 360  # Instead of 480
```

**Solution 2: Simplify Processing**
```python
# Line 118: Smaller kernel
kernel = np.ones((3, 3), np.uint8)  # Instead of 5x5
```

**Solution 3: Skip Frames**
```python
# Add after line 209
frame_skip = 2
if frame_count % frame_skip != 0:
    continue  # Skip this frame
```

---

### Problem: Grid overlay doesn't match physical grid

**Causes:**
1. Camera angle not perpendicular
2. Grid not fully visible
3. Lens distortion

**Solutions:**
1. Adjust camera to be directly above
2. Ensure entire grid in frame
3. Use wider angle or higher camera position
4. Consider perspective correction (advanced)

**Advanced: Perspective correction**
```python
# Detect grid corners and warp image
# (requires additional code - see OpenCV documentation)
```

---

## 🔌 Arduino-Specific Issues

### Problem: Serial port not found

**Windows:**
```powershell
# List available ports
python -c "import serial.tools.list_ports; [print(p.device) for p in serial.tools.list_ports.comports()]"
```

**Check:**
- Device Manager → Ports (COM & LPT)
- Note the COM port number
- Update SERIAL_PORT in serial_tracker.py

### Problem: Connection refused

**Solutions:**
1. Close Arduino IDE Serial Monitor
2. Check USB cable (try different cable)
3. Try different USB port
4. Verify baud rate matches (9600)

### Problem: Garbled data on Arduino

**Solutions:**
1. Verify baud rates match:
   - Python: `BAUD_RATE = 9600`
   - Arduino: `Serial.begin(9600);`
2. Check cable quality
3. Add delay in Arduino code

### Problem: LCD not displaying

**Solutions:**
1. Uncomment LCD code in arduino_receiver.ino
2. Install LiquidCrystal_I2C library
3. Verify I2C address (0x27 or 0x3F)
4. Check wiring (SDA, SCL, VCC, GND)

**Test I2C address:**
```cpp
// Upload I2C scanner sketch to Arduino
// Find the address and update line 20
```

---

## 🧪 Testing Methodology

### Test 1: Package Installation
```powershell
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "import numpy; print('NumPy:', numpy.__version__)"
python -c "import serial; print('PySerial: OK')"
```

### Test 2: Camera Access
```powershell
python -c "import cv2; cap=cv2.VideoCapture(0); ret,f=cap.read(); print('Resolution:', f.shape if ret else 'FAIL'); cap.release()"
```

### Test 3: Color Detection (Manual)
1. Run: `python hsv_calibration.py`
2. Verify: Object appears white in mask
3. Confirm: Background is black

### Test 4: Grid Alignment (Visual)
1. Run: `python OpenCV.py`
2. Press 'g' to show grid
3. Verify: Overlay matches physical grid

### Test 5: Coordinate Accuracy
1. Place object in known cell (e.g., top-left = 0,0)
2. Verify displayed coordinates match
3. Test all corners and center

### Test 6: Serial Communication (if using)
1. Upload arduino_receiver.ino
2. Open Arduino Serial Monitor
3. Run: `python serial_tracker.py`
4. Move object and verify coordinates appear

---

## 📊 Performance Benchmarks

### Expected Values:

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| FPS | 25-30 | 15-24 | <15 |
| Detection Rate | >95% | 80-95% | <80% |
| Latency | <40ms | 40-100ms | >100ms |
| False Positives | <1% | 1-5% | >5% |

### How to Measure:

**FPS:** Displayed in top-right corner
**Detection Rate:** % of frames with detection
**Latency:** Time from movement to display
**False Positives:** Wrong detections per minute

---

## 🆘 Still Having Issues?

### Diagnostic Script

Save as `diagnostic.py` and run:

```python
import sys
print("Python version:", sys.version)

try:
    import cv2
    print("OpenCV:", cv2.__version__, "✓")
except ImportError:
    print("OpenCV: NOT INSTALLED ✗")

try:
    import numpy
    print("NumPy:", numpy.__version__, "✓")
except ImportError:
    print("NumPy: NOT INSTALLED ✗")

try:
    import serial
    print("PySerial: INSTALLED ✓")
except ImportError:
    print("PySerial: NOT INSTALLED ✗")

try:
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        print(f"Camera 0: OK ({frame.shape[1]}x{frame.shape[0]}) ✓")
    else:
        print("Camera 0: OPENED but NO FRAME ✗")
    cap.release()
except:
    print("Camera 0: FAILED ✗")

print("\nIf all show ✓, your system is ready!")
```

---

## 🔄 Reset to Known Good State

If everything is broken, start fresh:

1. **Delete and recreate:**
```powershell
# Backup your HSV values first!
# Then download fresh copies of scripts
```

2. **Reinstall packages:**
```powershell
pip uninstall opencv-python numpy pyserial -y
pip install opencv-python numpy pyserial
```

3. **Test with minimal script:**
```python
import cv2
cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow('Test', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
```

If this works, gradually add features back.

---

## 📞 Getting Help

### Before Asking for Help:

1. ✅ Run diagnostic script above
2. ✅ Check error message carefully
3. ✅ Try solutions in this guide
4. ✅ Test with minimal script
5. ✅ Note what you've already tried

### Information to Provide:

- Operating system and version
- Python version
- OpenCV version
- Error message (full text)
- What you've tried so far
- Output of diagnostic script

---

## ✅ Success Checklist

Before considering the system "working":

- [ ] All packages installed
- [ ] Camera opens successfully
- [ ] Video feed displays
- [ ] Object is detected consistently
- [ ] Red circle appears on object
- [ ] Coordinates display correctly
- [ ] Grid overlay aligns (press 'g')
- [ ] All 25 cells accessible
- [ ] FPS is 15 or higher
- [ ] Can save frames (press 's')

If all checked → System is fully operational! 🎉

---

*Remember: 90% of issues are solved by proper HSV calibration and good lighting!*
