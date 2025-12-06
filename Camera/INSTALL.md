# Installation Requirements

## Python Dependencies

Install all required packages with a single command:

```powershell
pip install opencv-python numpy pyserial
```

Or use this requirements file:

```
opencv-python>=4.5.0
numpy>=1.19.0
pyserial>=3.5
```

Save as `requirements.txt` and install:
```powershell
pip install -r requirements.txt
```

## Individual Package Details

### opencv-python (cv2)
**Purpose:** Computer vision and image processing
**Size:** ~50 MB
**Functions used:**
- Video capture from webcam
- Image processing (color conversion, filtering)
- Contour detection
- Drawing functions

### numpy
**Purpose:** Numerical computations and arrays
**Size:** ~15 MB
**Functions used:**
- Array operations for HSV ranges
- Image representation as arrays
- Mathematical operations

### pyserial
**Purpose:** Serial communication with Arduino/microcontrollers
**Size:** ~80 KB
**Functions used:**
- Connect to COM ports
- Send coordinate data
- Receive acknowledgments

**Note:** Only needed if using `serial_tracker.py` for Arduino integration.

## Verify Installation

Run this command to verify all packages are installed correctly:

```powershell
python -c "import cv2, numpy, serial; print('All packages installed successfully!')"
```

## Python Version

**Minimum:** Python 3.8
**Recommended:** Python 3.10 or 3.11

Check your version:
```powershell
python --version
```

## Arduino Libraries (Optional)

If using Arduino integration, install via Arduino IDE Library Manager:

1. **LiquidCrystal I2C** (by Frank de Brabander)
   - For I2C LCD displays
   - Sketch → Include Library → Manage Libraries → Search "LiquidCrystal I2C"

## Troubleshooting Installation

### Windows

If pip is not recognized:
```powershell
python -m pip install opencv-python numpy pyserial
```

### Permission Issues (Linux/macOS)

```bash
pip install --user opencv-python numpy pyserial
```

### Behind Corporate Proxy

```powershell
pip install --proxy http://proxy.company.com:8080 opencv-python numpy pyserial
```

### Upgrade pip

If installation fails:
```powershell
python -m pip install --upgrade pip
```
