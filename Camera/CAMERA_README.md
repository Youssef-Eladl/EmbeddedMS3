# Camera System - Forge Registry Station

## Quick Start

### 1. Install Dependencies
```bash
pip install opencv-contrib-python numpy
```

### 2. Generate Aruco Markers
```bash
python generate_aruco.py
```
This creates markers with IDs 0-9. Print markers with ID 1 and ID 2 for the forge registry station.

### 3. Configure WiFi Connection
Edit `aruco_wifi_tracker.py`:
```python
PICO_IP = "192.168.1.100"  # Change to your Pico W's IP
PICO_PORT = 5000
CAMERA_INDEX = 0  # 0=default, 1=external USB camera
```

### 4. Run the Tracker
```bash
python aruco_wifi_tracker.py
```

## Controls

- **'q'** - Quit application
- **'g'** - Toggle grid overlay
- **'s'** - Save current frame as image

## Camera Setup

### Mounting
- Mount camera directly overhead
- Ensure entire 5×5 grid is visible in frame
- Maintain consistent lighting (avoid shadows)
- Height: Approximately 30-50cm above grid surface

### Calibration
1. Place a marker at known grid position
2. Verify reported coordinates match physical position
3. Adjust camera angle/position if needed
4. Grid cells are automatically calculated based on frame size

## Output Data Format

The tracker sends JSON packets to Pico W via UDP:

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

### Data Fields
- **id**: Aruco marker ID (1 or 2)
- **grid_row**: Row position (0-4, 0-indexed)
- **grid_col**: Column position (0-4, 0-indexed)
- **center_x**: Pixel X coordinate of marker center
- **center_y**: Pixel Y coordinate of marker center
- **area**: Marker size in pixels²

## Display Information

The tracker window shows:
- **Green grid overlay**: 5×5 grid divisions
- **Yellow boxes**: Detected markers with IDs
- **Grid coordinates**: 1-indexed for user display (1,1) to (5,5)
- **Highlighted cells**: Green for ID 1, Magenta for ID 2
- **Pico status**: Connection status and acknowledgments
- **FPS counter**: Real-time frame rate

## Troubleshooting

### No Markers Detected
- **Lighting**: Ensure bright, even lighting
- **Distance**: Move camera closer or farther from grid
- **Focus**: Ensure camera is in focus
- **Size**: Markers must be large enough (>1000 pixels²)
- **Dictionary**: Verify using DICT_4X4_50 markers

### Jittery Coordinates
- **Lighting**: Fix flickering lights or reflections
- **Mounting**: Stabilize camera mount (no vibration)
- **Processing**: Reduce frame rate if CPU overloaded

### WiFi Connection Issues
- **Same Network**: Ensure Pico W and PC on same WiFi
- **IP Address**: Verify Pico W's IP with serial monitor
- **Firewall**: Allow UDP port 5000
- **Ping Test**: Try `ping <PICO_IP>` from command line

### Performance Issues
- **Lower Resolution**: Change FRAME_WIDTH/FRAME_HEIGHT
- **Reduce FPS**: Change TARGET_FPS
- **Close Apps**: Free up CPU resources

## Configuration Options

### Adjustable Parameters

```python
# Network
PICO_IP = "192.168.1.100"  # Pico W IP address
PICO_PORT = 5000           # UDP port

# Camera
CAMERA_INDEX = 0           # Camera device index
FRAME_WIDTH = 640          # Frame width in pixels
FRAME_HEIGHT = 480         # Frame height in pixels
TARGET_FPS = 30            # Target frame rate

# Detection
ARUCO_DICT = cv2.aruco.DICT_4X4_50  # Aruco dictionary
MIN_MARKER_AREA = 1000     # Minimum marker size (pixels²)

# Communication
SEND_INTERVAL = 0.1        # Send updates every 100ms (10Hz)
```

## Technical Details

### Coordinate System
- **Origin**: Top-left corner is (0,0)
- **X-axis**: Left to right (columns)
- **Y-axis**: Top to bottom (rows)
- **Display**: Shows 1-indexed for user (1-5)
- **Internal**: Uses 0-indexed (0-4)

### Update Rate
- Camera captures at ~30 FPS
- Marker detection runs every frame
- Network updates sent at 10 Hz (configurable)
- Pico receives updates and sends acknowledgments

### Error Handling
- Automatic retry on send failures
- Non-blocking receive (10ms timeout)
- Graceful handling of network errors
- Marker validation (size threshold)

## Integration with Other Scripts

The `OpenCV.py` and `serial_tracker.py` scripts are legacy versions:
- **OpenCV.py**: Standalone marker tracking (no network)
- **serial_tracker.py**: Serial communication version
- **aruco_wifi_tracker.py**: Current WiFi version (use this one)

## Advanced Usage

### Multiple Markers
The system can track multiple markers simultaneously. The Pico firmware will:
1. Identify which marker ID is detected
2. Load appropriate target coordinates
3. Track that specific marker until placement complete

### Custom Grid Sizes
To change grid size, edit both Python and C code:
```python
GRID_SIZE = 5  # Python
```
```c
#define GRID_SIZE 5  // C code
```

### Debug Mode
Uncomment line in `receive_pico_response()` to see all network errors:
```python
print(f"ERROR receiving data: {e}")
```

---

**For complete system setup, see `FORGE_REGISTRY_SETUP.md`**
