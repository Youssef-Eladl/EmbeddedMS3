# Build Notes

## Successful Build

The project has been successfully compiled! Output files:
- **EmbeddedMS3.uf2** (685 KB) - Flash this to Pico W
- EmbeddedMS3.elf (1.8 MB) - ELF executable
- EmbeddedMS3.bin (342 KB) - Raw binary
- EmbeddedMS3.hex (964 KB) - Hex format

## Important: lwIP Configuration

The build requires a custom `lwipopts.h` file that is generated during the first build. This file is located at:
```
build/pico-sdk/src/rp2_common/pico_cyw43_driver/lwipopts.h
```

**Note:** If you do a clean rebuild, you'll need to recreate this file. The file has been configured for:
- UDP support (required for WiFi communication)
- DHCP for automatic IP assignment
- Threadsafe background WiFi operation
- Optimized memory settings

## Rebuilding

For normal rebuilds (after code changes):
```powershell
cd build
ninja
```

For clean rebuilds:
```powershell
cd build
Remove-Item -Recurse -Force *
cmake -G Ninja ..
# Manually copy lwipopts.h if needed (see below)
ninja
```

## Preserving lwipopts.h

If you need to do frequent clean rebuilds, save the lwipopts.h file:

```powershell
# Backup
Copy-Item "build\pico-sdk\src\rp2_common\pico_cyw43_driver\lwipopts.h" "lwipopts_backup.h"

# After clean rebuild, restore:
New-Item -ItemType Directory -Force -Path "build\pico-sdk\src\rp2_common\pico_cyw43_driver"
Copy-Item "lwipopts_backup.h" "build\pico-sdk\src\rp2_common\pico_cyw43_driver\lwipopts.h"
```

Or simply use incremental builds with `ninja` which is much faster anyway.

## Next Steps

1. **Flash firmware:**
   - Hold BOOTSEL button on Pico W
   - Connect USB
   - Copy `build/EmbeddedMS3.uf2` to RPI-RP2 drive

2. **Configure before flashing:**
   - Edit WiFi credentials in `EmbeddedMS3.c` (lines 92-93)
   - Edit QR code sequence in `EmbeddedMS3.c` (line 118)
   - Rebuild with `ninja`

3. **Setup Python camera:**
   ```powershell
   cd Camera
   pip install -r requirements.txt
   python test_system.py  # Test first
   python aruco_wifi_tracker.py  # Run tracker
   ```

4. **Monitor serial output:**
   - Open serial monitor at 115200 baud
   - Note the IP address displayed
   - Update `PICO_IP` in `aruco_wifi_tracker.py`

## Build Configuration

The project is configured for:
- **Board:** Pico W (pico_w)
- **WiFi:** CYW43 with lwIP threadsafe background
- **Libraries:** ADC, PWM, I2C, WiFi/UDP
- **Optimization:** -O3 (Release mode)
- **stdio:** Both UART and USB enabled

## Troubleshooting

**"Cannot find lwipopts.h":**
- The file should auto-generate, but sometimes doesn't
- Use the backup method above
- Or contact support with build log

**"MEM_LIBC_MALLOC incompatible":**
- Already fixed in current lwipopts.h
- Ensure `MEM_LIBC_MALLOC` is set to `0`

**WiFi/lwIP errors:**
- Verify `PICO_BOARD` is set to `pico_w` in CMakeLists.txt
- Check all WiFi libraries are linked correctly

---

**Build Status:** ✅ SUCCESS  
**Firmware Size:** 685 KB  
**Ready to Flash:** YES
