# Red Blob Tracking - Electromagnet Position Verification

## Overview
The Python camera script now tracks both **ArUco markers** (plate positions) and a **red blob** (electromagnet position). When the red blob (electromagnet) is verified to be at the target position for 5 consecutive seconds, the system automatically sends a RELEASE command to turn off the electromagnet.

## How It Works

### 1. Red Blob Detection
The script uses HSV color space to detect red objects:
- **Primary red range**: HSV(0-10, 120-255, 70-255)
- **Secondary red range**: HSV(170-180, 120-255, 70-255) (wraps around hue wheel)
- **Minimum blob area**: 100 pixels (configurable via `MIN_BLOB_AREA`)

### 2. Position Verification
- The largest detected ArUco marker sets the target position
- The system tracks if the red blob stays within the target grid cell
- A progress bar shows verification status (0-100%)
- After 5 seconds of continuous presence at the target, RELEASE is triggered

### 3. Visual Feedback
On the camera display:
- **Red crosshair + circle**: Shows blob position
- **Green crosshair + circle**: Blob verified at target
- **Progress bar**: Shows % completion of 5-second verification
- **Status text**: "Blob Detected" → "Verifying: X%" → "VERIFIED - RELEASED"

### 4. Serial Communication
When verified, sends: `RELEASE\n` to the Pico
The Pico firmware parses this command and calls `magnet_set(false)` to turn off GPIO8

## Configuration

### Python Script (`aruco_wifi_tracker.py`)
```python
# Red Blob Detection (Electromagnet)
LOWER_RED_HSV = np.array([0, 120, 70])
UPPER_RED_HSV = np.array([10, 255, 255])
LOWER_RED_HSV_ALT = np.array([170, 120, 70])
UPPER_RED_HSV_ALT = np.array([180, 255, 255])
MIN_BLOB_AREA = 100
VERIFY_DURATION = 5.0  # Hold target position for 5 seconds
```

### Tuning Red Detection
If the red blob is not detected or falsely triggered:
1. Run `hsv_calibration.py` to find optimal HSV ranges for your lighting
2. Adjust `LOWER_RED_HSV` and `UPPER_RED_HSV` values
3. Increase `MIN_BLOB_AREA` to filter out small red reflections
4. Decrease `MIN_BLOB_AREA` if the electromagnet is small and not detected

### Pico Firmware (`EmbeddedMS3.c`)
The `handle_serial_line()` function now handles two message types:
```c
// ArUco marker position: "id,row,col\n"
// Release command: "RELEASE\n"
```

## Workflow Example

1. **Plate 1 detected**: ArUco marker ID 1 at grid position (3,2)
2. **Magnet pickup**: Electromagnet turns on, picks up plate
3. **Movement**: Potentiometer control moves gantry
4. **Blob tracking begins**: Red blob detected at (1,1)
5. **Blob approaches target**: Blob moves to (3,2)
6. **Verification starts**: Timer begins (0% → 100%)
7. **Verification complete**: After 5 seconds at (3,2), RELEASE sent
8. **Magnet release**: GPIO8 turned off, plate drops

## Testing

### Test Red Blob Detection Only
1. Place a red object (e.g., red tape on electromagnet) in camera view
2. Run `python aruco_wifi_tracker.py`
3. Verify red crosshair appears on the red object
4. Check console for blob detection messages

### Test Full Workflow
1. Place ArUco marker at target position
2. Move red blob (electromagnet) around the grid
3. Position blob at same grid cell as marker
4. Hold steady for 5 seconds
5. Watch progress bar fill up
6. Verify "VERIFIED - RELEASED" appears
7. Check Pico serial output for "RELEASE command received"

## Troubleshooting

### Red blob not detected
- Check HSV ranges match your red object color
- Verify lighting conditions (bright overhead light helps)
- Lower `MIN_BLOB_AREA` threshold
- Use `hsv_calibration.py` to find optimal values

### False detections
- Increase `MIN_BLOB_AREA` to filter noise
- Narrow HSV ranges to be more selective
- Remove other red objects from camera view

### Verification never completes
- Ensure blob stays perfectly still at target for 5 seconds
- Check that grid position calculation is correct
- Reduce `VERIFY_DURATION` for faster testing
- Verify ArUco marker is detected (sets target position)

### RELEASE not working on Pico
- Check serial connection (COM3 at 115200 baud)
- Verify Pico firmware flashed with updated code
- Check console output for "SER RX -> RELEASE command received"
- Test magnet GPIO8 independently

## LED Status Indicators
(If you add status LEDs to the Pico)
- **Green LED**: ArUco marker detected
- **Yellow LED**: Blob detected
- **Blue LED**: Verification in progress
- **White LED**: Verified and released

## Future Enhancements
- [ ] Add timeout if verification takes too long
- [ ] Support multiple target positions
- [ ] Add "PICKUP" command when blob leaves magnet zone
- [ ] Track blob path history for debugging
- [ ] Add blob size verification (ensure it's the right object)
- [ ] Support different colored blobs for multiple tools
