# Build Instructions for Forge Registry Station

## Prerequisites

- Raspberry Pi Pico SDK installed
- CMake and Ninja build tools
- VS Code with Pico extension (recommended)

## Build Steps

### Windows (PowerShell)

```powershell
# Navigate to build directory
cd build

# Clean previous build (if needed)
Remove-Item -Recurse -Force *

# Configure CMake
cmake -G Ninja ..

# Build the project
ninja

# The output file will be: EmbeddedMS3.uf2
```

### Linux/Mac

```bash
# Navigate to build directory
cd build

# Clean previous build (if needed)
rm -rf *

# Configure CMake
cmake ..

# Build the project
make -j4

# The output file will be: EmbeddedMS3.uf2
```

## Flashing to Pico W

1. **Enter BOOTSEL Mode:**
   - Hold the BOOTSEL button on Pico W
   - Connect USB cable to PC
   - Release BOOTSEL button
   - Pico W appears as USB drive "RPI-RP2"

2. **Copy Firmware:**
   - Copy `build/EmbeddedMS3.uf2` to the RPI-RP2 drive
   - Pico W will automatically reboot and run the program

3. **Monitor Serial Output:**
   - Open serial monitor at 115200 baud
   - You'll see WiFi connection status and IP address

## Using VS Code Tasks

If you have VS Code with Pico extension:

```
Ctrl+Shift+B → Select "Compile Project"
```

This runs the build automatically.

## Troubleshooting Build Issues

### "Command not found: cmake"
- Install CMake: https://cmake.org/download/
- Add to PATH environment variable

### "Command not found: ninja"
- VS Code Pico extension should install this
- Or install manually: https://github.com/ninja-build/ninja/releases

### "Cannot find pico_sdk_import.cmake"
- Ensure Pico SDK is installed
- Set PICO_SDK_PATH environment variable

### "WiFi/lwIP errors"
- Verify PICO_BOARD is set to "pico_w" in CMakeLists.txt
- Check line 26: `set(PICO_BOARD pico_w CACHE STRING "Board type")`

### "Undefined reference to..."
- Check target_link_libraries in CMakeLists.txt
- Ensure all required libraries are included:
  - pico_stdlib
  - pico_cyw43_arch_lwip_threadsafe_background
  - hardware_adc
  - hardware_pwm
  - hardware_i2c

## Build Output Files

After successful build, you'll find in `build/`:

- **EmbeddedMS3.uf2** - Main firmware file (flash this)
- **EmbeddedMS3.elf** - ELF executable (for debugging)
- **EmbeddedMS3.bin** - Raw binary
- **EmbeddedMS3.dis** - Disassembly listing
- **compile_commands.json** - For IDE IntelliSense

## Verify Build

Check the output for:
```
[100%] Built target EmbeddedMS3
```

Verify UF2 file size:
- Should be ~300-500 KB
- Much larger = debug symbols included (OK)
- Much smaller = incomplete build

## Configuration Before Building

### 1. Edit WiFi Credentials
File: `EmbeddedMS3.c` lines 92-93
```c
#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"
```

### 2. Edit QR Code Sequence
File: `EmbeddedMS3.c` line 118
```c
static int qr_sequence[4] = {5, 4, 3, 2}; // Your QR code
```

### 3. Adjust LCD I2C Address (if needed)
File: `EmbeddedMS3.c` line 88
```c
#define LCD_ADDR        0x27 // Try 0x3F if LCD doesn't work
```

## Rebuild After Changes

```powershell
cd build
ninja
# Flash the new EmbeddedMS3.uf2
```

## Clean Build

If you encounter build errors:
```powershell
cd build
Remove-Item -Recurse -Force *
cmake -G Ninja ..
ninja
```

## Build Time

- First build: ~1-3 minutes (compiles SDK)
- Incremental: ~5-15 seconds (only changed files)

## Success Indicators

After flashing and power-on:
1. Pico W LED blinks during WiFi connection
2. Serial output shows: "WiFi connected!"
3. Serial shows IP address: "IP: 192.168.1.xxx"
4. LCD displays: "WIFI CONNECTED"
5. System proceeds to homing sequence

---

**Next Step:** Configure Python camera tracker with the IP address shown in serial monitor
