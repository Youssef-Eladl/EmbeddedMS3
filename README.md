# EmbeddedMS3 – Forge Registry Station (All-In-One Guide)

USB-serial ArUco tracker + dual-potentiometer H-bot gantry control. This README replaces all other READMEs/quickstarts—treat it as the single source of truth (legacy docs remain in the repo for history only).

## What This Does
- Camera detects ArUco plates on a 5×5 grid.
- Python script sends the top marker’s grid cell to the Pico over the same USB cable that powers it (115200 baud CSV: `id,row,col`).
- Pico homes, shows targets on a 16×2 LCD, and lets you move the gantry with two potentiometers mapped for H-bot kinematics: X pot drives both motors the same way (neg X → both CCW), Y pot drives motors in opposite directions.
- Hold at the target for 5 seconds to place/release via the electromagnet; UV LED lights on success.

## Hardware & Pin Map (edit in `EmbeddedMS3.c` under **PIN DEFINITIONS**)
Update the pins below to match your build; defaults are provided.

| Function            | Default Pin | Notes |
|---------------------|-------------|-------|
| I2C SDA / SCL       | 0 / 1       | 16×2 LCD backpack |
| Motor A PWM / DIR   | 15 / 17&16  | H-bot left/primary motor (ENA=15, IN1=17, IN2=16) |
| Motor B PWM / DIR   | 13 / 19&18  | H-bot right/secondary motor (ENB=13, IN3=19, IN4=18) |
| Limit X / Y         | 6 / 7       | Pulled-up, active low |
| Electromagnet       | 8           | Active high |
| Start Button        | 9           | Active low (start stages) |
| Buzzer              | 10          | Active high |
| UV LED              | 11          | Active high |
| Pot X (ADC0)        | 26          | X pot drives both motors same direction (neg → CCW) |
| Pot Y (ADC1)        | 27          | Y pot drives motors opposite |

Key tunables (top of `EmbeddedMS3.c`):
- `qr_sequence` → two target cells encoded by your QR clue (e.g., `{5,4,3,2}` → (5,4) then (3,2)).
- `DEADZONE` for pots, adjust if your center drifts.

## Build & Flash (Pico, USB serial only)
1) From repo root: `cd build`; if first time: `cmake ..`
2) Build: `ninja` (or run the **Compile Project** VS Code task).
3) Flash `build/EmbeddedMS3.uf2` to the Pico (drag-drop or your usual flasher).

## Camera Tracker (Python → USB Serial)
1) `cd Camera`
2) Install deps: `pip install -r requirements.txt` (needs OpenCV with ArUco + pyserial)
3) Set the Pico’s COM port: edit `SERIAL_PORT` in `aruco_wifi_tracker.py` (now a serial tracker).
4) Run: `python aruco_wifi_tracker.py`
5) The script streams `id,row,col` every 100 ms (largest marker wins). Grid is 0-indexed internally.

## Runtime Controls
- **Start button (pin 9):** begin plate handling when a marker is seen at (1,1).
- **Pot X (ADC0):** drives both H-bot motors same direction (neg → both CCW = -X).
- **Pot Y (ADC1):** drives motors opposite directions for Y travel.
- **LCD:** shows targets and current cell from the camera feed.
- **Magnet:** auto-engages on pick, auto-releases after a 5-second stable hold at the target.
- **UV LED:** turns on when both plates are placed successfully.

## Data Format (Camera → Pico)
- CSV line over USB CDC: `id,row,col\n`
- Example: `1,2,3` = marker ID 1 detected at grid row 2, col 3 (0-indexed).

## Typical Flow
1) Power Pico via USB; open a serial terminal at 115200 for logs (optional).
2) Run the Python tracker; verify it connects to the Pico’s COM port.
3) Place marker at (1,1); press Start to grab with the magnet.
4) Move with the X/Y potentiometers toward the target shown on LCD (H-bot mapping: X = both motors same direction, Y = opposite).
5) Hold within target cell for 5 seconds → magnet releases; repeat for second plate → UV LED on success.

## Troubleshooting
- **No serial port:** replug Pico, check Device Manager/`ls /dev/tty*`, update `SERIAL_PORT`.
- **No position updates:** confirm camera sees markers; ensure tracker window shows IDs and grid cells; verify CSV prints in terminal.
- **Pot center drift:** increase/decrease `DEADZONE` in `EmbeddedMS3.c`.
- **Direction feels inverted:** swap motor leads or invert dir pins; X should drive both motors same way (neg X = both CCW), Y should drive motors opposite.
- **Diagonal skew:** check belt tension and that both motors rotate evenly (H-bot requires matched speeds).

## File Map (essentials)
- `EmbeddedMS3.c` – Pico firmware (USB serial input, button queue, LCD, state machine).
 - `EmbeddedMS3.c` – Pico firmware (USB serial input, pot-driven H-bot mapping, LCD, state machine).
- `CMakeLists.txt` – build config (no WiFi libs).
- `Camera/aruco_wifi_tracker.py` – serial ArUco tracker (USB CDC output).
- `Camera/requirements.txt` – Python deps.
- Legacy docs retained: `QUICKSTART.md`, `FORGE_REGISTRY_SETUP.md`, `WIRING_DIAGRAM.md`, `Camera/CAMERA_README.md` (superseded by this README).
