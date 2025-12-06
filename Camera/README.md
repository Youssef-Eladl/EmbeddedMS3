# 5×5 Grid Object Tracking System - Complete Setup Guide

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Hardware Requirements](#hardware-requirements)
3. [Software Installation](#software-installation)
4. [Physical Grid Setup](#physical-grid-setup)
5. [Color Calibration](#color-calibration)
6. [Running the System](#running-the-system)
7. [Arduino Integration (Optional)](#arduino-integration-optional)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)

---

## 🎯 System Overview

This computer vision system tracks a colored object moving on a 5×5 physical grid using your laptop's webcam. It uses OpenCV for image processing and outputs real-time grid coordinates.

**Key Features:**
- Real-time object tracking (≥20 FPS)
- HSV color-based detection
- Visual grid overlay
- Console and on-screen coordinate display
- Optional serial output to Arduino/ESP32
- Interactive calibration tool

---

## 🔧 Hardware Requirements

### Required:
- **Laptop/PC** with built-in or external webcam
- **Physical 5×5 grid** (see construction details below)
- **Tracking object** (colored ball, cap, or piece)

### Optional:
- **Arduino Uno/Mega/Nano** or **ESP32** for external display
- **16×2 I2C LCD Display** for standalone position readout
- **Camera mount/tripod** for stable top-down positioning

### Camera Setup:
- Position camera **directly above** the grid (top-down view)
- Ensure entire grid is visible in frame
- Height: 30-50 cm above grid (adjust based on camera FOV)
- Fixed position (no movement during operation)
- Good lighting (avoid shadows and glare)

---

## 💻 Software Installation

### Step 1: Install Python
Ensure Python 3.8 or higher is installed:
```powershell
python --version
```

### Step 2: Install Required Libraries
```powershell
pip install opencv-python numpy pyserial
```

**Library Purposes:**
- `opencv-python` (cv2): Image processing and webcam access
- `numpy`: Numerical operations and array handling
- `pyserial`: Serial communication with Arduino (optional)

### Step 3: Verify Installation
```powershell
python -c "import cv2; import numpy; print('OpenCV version:', cv2.__version__)"
```

Expected output: `OpenCV version: 4.x.x`

---

## 📐 Physical Grid Setup

### Grid Specifications

**Recommended Dimensions:**
- **Total size:** 25 cm × 25 cm (10 inches × 10 inches)
- **Cell size:** 5 cm × 5 cm each (2 inches × 2 inches)
- **Grid lines:** 3-5 mm thick, dark black
- **Background:** White or light-colored

### Construction Methods

#### Method 1: Printed Grid (Easiest)
1. Print the provided template on A4/Letter paper
2. Use thick black lines for better detection
3. Mount on cardboard for rigidity
4. Laminate for durability (optional)

#### Method 2: Hand-Drawn Grid
Materials:
- White cardboard or foam board (25×25 cm)
- Black permanent marker (thick tip)
- Ruler

Steps:
1. Mark 5 cm intervals on all four edges
2. Draw horizontal lines connecting marks
3. Draw vertical lines connecting marks
4. Ensure lines are thick (3-5 mm) and dark

#### Method 3: Tape Grid
Materials:
- White surface (table, paper, board)
- Black electrical tape (15-20 mm wide)

Steps:
1. Apply horizontal tape strips at 5 cm intervals
2. Apply vertical tape strips at 5 cm intervals
3. Ensure tape is flat and firmly adhered

### Grid Coordinate System
```
     Col: 0    1    2    3    4
Row 0: ┌────┬────┬────┬────┬────┐
       │    │    │    │    │    │
Row 1: ├────┼────┼────┼────┼────┤
       │    │    │    │    │    │
Row 2: ├────┼────┼────┼────┼────┤
       │    │    │  ● │    │    │  ← Object at (2, 2)
Row 3: ├────┼────┼────┼────┼────┤
       │    │    │    │    │    │
Row 4: └────┴────┴────┴────┴────┘
```

**Coordinate Convention:**
- Origin (0,0) is **top-left** corner
- Format: **(row, column)**
- Rows: 0-4 (top to bottom)
- Columns: 0-4 (left to right)

---

## 🎨 Color Calibration

### Choosing Your Tracking Object

The object should:
- Have **distinct, solid color** (red, green, blue, yellow, orange)
- Contrast with grid background
- Be 2-4 cm in diameter (fills ~50% of one cell)
- Have matte finish (avoid shiny/reflective objects)

**Best Object Examples:**
- ✅ Red ping-pong ball
- ✅ Blue bottle cap
- ✅ Green toy block
- ✅ Yellow sticky note ball
- ❌ White/black objects (low contrast)
- ❌ Multi-colored objects

### HSV Color Space Basics

**Why HSV instead of RGB?**
- More robust to lighting changes
- Easier to define color ranges
- Better for color segmentation

**HSV Components:**
- **H (Hue):** Color type (0-179 in OpenCV)
  - Red: 0-10, 170-179
  - Green: 40-80
  - Blue: 100-130
  - Yellow: 20-30
- **S (Saturation):** Color intensity (0-255)
  - Higher = more vivid
  - Lower = more washed out
- **V (Value):** Brightness (0-255)
  - Higher = brighter
  - Lower = darker

### Using the Calibration Tool

1. **Run the calibration script:**
```powershell
python hsv_calibration.py
```

2. **Position your object** in the camera view

3. **Adjust trackbars** until:
   - Object appears **WHITE** in "Mask" window
   - Everything else appears **BLACK**
   - Mask should be solid (no holes)

4. **Press 's'** to save values to `hsv_values.txt`

5. **Copy values** to `OpenCV.py` (lines 17-23)

### Common HSV Ranges (Starting Points)

```python
# Red objects
LOWER_HSV = np.array([0, 120, 70])
UPPER_HSV = np.array([10, 255, 255])
LOWER_HSV_ALT = np.array([170, 120, 70])  # Red wraps around
UPPER_HSV_ALT = np.array([180, 255, 255])

# Green objects
LOWER_HSV = np.array([40, 40, 40])
UPPER_HSV = np.array([80, 255, 255])

# Blue objects
LOWER_HSV = np.array([100, 100, 100])
UPPER_HSV = np.array([130, 255, 255])

# Yellow objects
LOWER_HSV = np.array([20, 100, 100])
UPPER_HSV = np.array([30, 255, 255])

# Orange objects
LOWER_HSV = np.array([10, 100, 100])
UPPER_HSV = np.array([20, 255, 255])
```

---

## 🚀 Running the System

### Quick Start

1. **Position camera** above grid (top-down view)
2. **Verify grid is fully visible** in camera frame
3. **Run main script:**
```powershell
python OpenCV.py
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `g` | Toggle grid overlay on/off |
| `h` | Toggle cell highlighting on/off |
| `s` | Save current frame as image |

### What You Should See

**On Screen:**
- Live camera feed with grid overlay
- Green highlighting on active cell
- Red dot on object centroid
- Position text: `Position: (row, col)`
- FPS counter (top-right)

**In Console:**
```
Object Position: (2, 3) | Pixel: (384, 256) | Area: 523
```

### Configuration Options

Edit `OpenCV.py` to customize:

```python
# Line 26-27: Grid size
GRID_SIZE = 5  # Change for different grid sizes

# Line 28: Minimum detection area
MIN_OBJECT_AREA = 100  # Increase to filter smaller objects

# Line 31-34: Camera settings
CAMERA_INDEX = 0       # 0=built-in, 1=external
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
TARGET_FPS = 30

# Line 37-40: Display toggles
SHOW_GRID_OVERLAY = True
SHOW_DETECTION_CIRCLE = True
SHOW_CELL_HIGHLIGHT = True
SHOW_FPS = True
```

---

## 🔌 Arduino Integration (Optional)

### Hardware Setup

**Wiring for LCD Display:**
```
LCD Module    →    Arduino Pin
---------          -----------
VCC          →     5V
GND          →     GND
SDA          →     A4 (Uno) / GPIO21 (ESP32)
SCL          →     A5 (Uno) / GPIO22 (ESP32)
```

### Arduino Setup

1. **Install Arduino IDE** from arduino.cc

2. **Install LCD Library:**
   - Open Arduino IDE
   - Go to: Tools → Manage Libraries
   - Search: "LiquidCrystal I2C"
   - Install by Frank de Brabander

3. **Upload Code:**
   - Open `arduino_receiver.ino`
   - Select board: Tools → Board → Arduino Uno (or your board)
   - Select port: Tools → Port → COM3 (or your port)
   - Click Upload

4. **Find I2C Address:**
```cpp
// Run I2C scanner sketch to find your LCD address
// Common addresses: 0x27 or 0x3F
```

### Python Serial Setup

1. **Find COM Port:**
```powershell
python -c "import serial.tools.list_ports; [print(p.device) for p in serial.tools.list_ports.comports()]"
```

2. **Edit `serial_tracker.py`:**
```python
# Line 18: Change to your port
SERIAL_PORT = 'COM3'  # Windows
# SERIAL_PORT = '/dev/ttyUSB0'  # Linux
# SERIAL_PORT = '/dev/cu.usbserial-XXX'  # macOS

# Line 19: Match Arduino baud rate
BAUD_RATE = 9600
```

3. **Run with Serial:**
```powershell
python serial_tracker.py
```

### Serial Data Format

**Sent from Python to Arduino:**
```
"ROW,COL\n"
Example: "2,4\n"
```

**Received from Arduino (acknowledgment):**
```
"ACK\n"
```

---

## 🔍 Troubleshooting

### Camera Issues

**Problem:** Camera not detected
```powershell
# Test different camera indices
python -c "import cv2; cap = cv2.VideoCapture(0); print('Works!' if cap.isOpened() else 'Failed'); cap.release()"
```
**Solution:** Try `CAMERA_INDEX = 1` or `2`

**Problem:** Poor frame rate
- Close other applications using camera
- Reduce `FRAME_WIDTH` and `FRAME_HEIGHT`
- Improve lighting

### Detection Issues

**Problem:** Object not detected
- Run `hsv_calibration.py` and recalibrate
- Increase lighting
- Use more contrasting object color
- Lower `MIN_OBJECT_AREA` value

**Problem:** False detections
- Narrow HSV range (adjust saturation/value)
- Increase `MIN_OBJECT_AREA`
- Remove background objects with similar colors
- Improve grid contrast

**Problem:** Flickering coordinates
- Increase `MIN_OBJECT_AREA` to stabilize
- Improve lighting consistency
- Use solid-color object (avoid patterns)

### Grid Overlay Issues

**Problem:** Grid doesn't align with physical grid
- Ensure entire grid is visible in frame
- Camera must be level (parallel to grid)
- Adjust camera height/angle
- Consider perspective correction (advanced)

### Serial Communication Issues

**Problem:** Connection failed
- Verify COM port with Device Manager (Windows)
- Close Arduino IDE Serial Monitor (port conflict)
- Check cable connection
- Try different USB port

**Problem:** Garbled data
- Verify baud rates match (both 9600)
- Check for loose connections
- Add delay in Arduino code

---

## ⚡ Performance Optimization

### Speed Improvements

1. **Reduce Resolution:**
```python
FRAME_WIDTH = 480   # Instead of 640
FRAME_HEIGHT = 360  # Instead of 480
```

2. **Skip Frame Processing:**
```python
frame_skip = 2
if frame_count % frame_skip == 0:
    # Process frame
```

3. **Simplify Morphology:**
```python
kernel = np.ones((3, 3), np.uint8)  # Smaller kernel
```

### Accuracy Improvements

1. **Better Lighting:**
   - Use diffused lighting
   - Avoid shadows
   - Consistent brightness

2. **Tighter HSV Ranges:**
   - Narrow saturation range
   - Adjust for ambient lighting

3. **Perspective Correction:**
   - Use `cv2.getPerspectiveTransform()`
   - Detect grid corners automatically
   - Warp frame to perfect top-down view

### Advanced Features

**Smooth Coordinate Transitions:**
```python
# Add to main loop (exponential moving average)
alpha = 0.3
if prev_row is not None:
    row = int(alpha * row + (1 - alpha) * prev_row)
    col = int(alpha * col + (1 - alpha) * prev_col)
```

**Multi-Object Tracking:**
- Track multiple contours
- Assign unique IDs
- Maintain object history

**Path Recording:**
- Store coordinate history
- Visualize path over time
- Export to CSV for analysis

---

## 📊 Expected Performance

| Metric | Target | Typical |
|--------|--------|---------|
| FPS | ≥20 | 25-30 |
| Detection Latency | <50ms | 30-40ms |
| Position Accuracy | ±1 cell | Perfect in good conditions |
| Startup Time | <5s | 2-3s |

---

## 🎓 Understanding the Detection Method

### Why HSV Color Thresholding?

**Advantages:**
- ✅ Robust to lighting variations
- ✅ Intuitive color selection
- ✅ Fast processing (real-time capable)
- ✅ Simple implementation

**Alternatives (not used here):**
- Template matching: Slower, requires specific object shape
- Deep learning: Overkill, requires training data
- Feature detection: Complex, unnecessary for solid colors

### Processing Pipeline

1. **Capture Frame** → BGR image from camera
2. **Color Space Conversion** → BGR to HSV
3. **Color Thresholding** → Binary mask (white=object, black=background)
4. **Morphological Operations** → Remove noise, fill holes
5. **Contour Detection** → Find object boundaries
6. **Centroid Calculation** → Image moments → (cx, cy)
7. **Coordinate Mapping** → Pixels → Grid cells
8. **Visualization** → Draw overlays
9. **Output** → Display & Serial transmission

### Why Image Moments for Centroid?

Image moments calculate the "center of mass" of the detected region:
```python
M = cv2.moments(contour)
cx = int(M["m10"] / M["m00"])  # x centroid
cy = int(M["m01"] / M["m00"])  # y centroid
```

This is more accurate than using bounding box center, especially for irregular shapes.

---

## 📝 Files Overview

| File | Purpose |
|------|---------|
| `OpenCV.py` | Main tracking script |
| `hsv_calibration.py` | Interactive color calibration tool |
| `serial_tracker.py` | Tracking with Arduino serial output |
| `arduino_receiver.ino` | Arduino code for receiving coordinates |
| `README.md` | This documentation |

---

## 🚀 Quick Start Checklist

- [ ] Install Python 3.8+
- [ ] Install: `pip install opencv-python numpy`
- [ ] Build physical 5×5 grid (25×25 cm)
- [ ] Choose colored tracking object
- [ ] Position camera above grid
- [ ] Run: `python hsv_calibration.py`
- [ ] Calibrate HSV ranges, press 's' to save
- [ ] Update HSV values in `OpenCV.py`
- [ ] Run: `python OpenCV.py`
- [ ] Verify detection and coordinates
- [ ] (Optional) Setup Arduino with `arduino_receiver.ino`
- [ ] (Optional) Run: `python serial_tracker.py`

---

## 🎯 Next Steps & Enhancements

1. **Automatic Grid Detection**
   - Detect grid corners using Hough lines
   - Apply perspective transform
   - Auto-calibrate coordinate mapping

2. **Multiple Object Tracking**
   - Track different colored objects simultaneously
   - Collision detection
   - Interactive games

3. **Data Logging**
   - Record position history
   - Export to CSV/JSON
   - Analyze movement patterns

4. **Robot Control**
   - Interface with robotic arm
   - Implement pick-and-place
   - Autonomous navigation

5. **Web Interface**
   - Stream video over network
   - Remote monitoring
   - Web-based controls

---

## 📞 Support & Resources

**OpenCV Documentation:** https://docs.opencv.org/
**Color Space Tutorial:** https://docs.opencv.org/master/df/d9d/tutorial_py_colorspaces.html
**Serial Communication:** https://pyserial.readthedocs.io/

---

**System Ready! Place your object on the grid and start tracking!** 🎉
