# Wiring Diagram - Forge Registry Station

## Complete Wiring Guide

### Power Distribution
```
12V Power Supply (Motors)
    ├─→ Motor Driver VCC
    └─→ Electromagnet Driver VCC

5V Power Supply (Logic)
    ├─→ Pico W VSYS (Pin 39)
    ├─→ LCD VCC
    ├─→ Motor Driver Logic VCC
    └─→ Electromagnet Driver Logic VCC

GND (Common Ground)
    ├─→ Pico W GND (Pin 38)
    ├─→ Motor Driver GND
    ├─→ LCD GND
    ├─→ All sensors/switches
    └─→ Power supplies GND
```

## Detailed Pin Connections

### 1. Potentiometers (Analog Inputs)

**X-Axis Potentiometer (10kΩ)**
```
Pin 1 (CCW) → GND
Pin 2 (Wiper) → Pico GPIO 26 (ADC0, Pin 31)
Pin 3 (CW) → 3.3V (Pin 36)
```

**Y-Axis Potentiometer (10kΩ)**
```
Pin 1 (CCW) → GND
Pin 2 (Wiper) → Pico GPIO 27 (ADC1, Pin 32)
Pin 3 (CW) → 3.3V (Pin 36)
```

### 2. DC Motor Driver (L298N - X Axis)

**Motor Driver → Pico W**
```
IN1 → Pico GPIO 3 (Direction, Pin 5)
IN2 → GND (or use for reverse if needed)
ENA → Pico GPIO 2 (PWM, Pin 4)
```

**Motor Driver → X-Axis Motor**
```
OUT1 → Motor Terminal 1
OUT2 → Motor Terminal 2
```

**Motor Driver → Power**
```
12V → 12V Supply
GND → Common GND
5V → 5V Logic Supply
```

### 3. DC Motor Driver (L298N - Y Axis)

**Motor Driver → Pico W**
```
IN1 → Pico GPIO 5 (Direction, Pin 7)
IN2 → GND
ENA → Pico GPIO 4 (PWM, Pin 6)
```

**Motor Driver → Y-Axis Motor**
```
OUT1 → Motor Terminal 1
OUT2 → Motor Terminal 2
```

### 4. Limit Switches (Homing)

**X-Axis Limit Switch**
```
NO (Normally Open) → Pico GPIO 6 (Pin 9)
COM → GND
```
*Internal pull-up enabled in software*

**Y-Axis Limit Switch**
```
NO (Normally Open) → Pico GPIO 7 (Pin 10)
COM → GND
```
*Internal pull-up enabled in software*

### 5. Electromagnet Circuit

**Using Relay Module**
```
VCC → 5V
GND → GND
IN → Pico GPIO 8 (Pin 11)
NO (Normally Open) → Electromagnet (+)
COM → 12V Supply (+)
Electromagnet (-) → Power Supply GND
```

**Using Transistor (NPN - 2N2222 or similar)**
```
Pico GPIO 8 (Pin 11) → 1kΩ Resistor → Transistor Base
Transistor Emitter → GND
Transistor Collector → Electromagnet (-)
Electromagnet (+) → 12V Supply (+)
Flyback Diode (1N4007) across electromagnet (cathode to +12V)
```

### 6. 16×2 LCD with I2C Backpack

**LCD I2C Module → Pico W**
```
VCC → 5V (Pin 40)
GND → GND (Pin 38)
SDA → Pico GPIO 0 (I2C0 SDA, Pin 1)
SCL → Pico GPIO 1 (I2C0 SCL, Pin 2)
```

*Note: I2C address is typically 0x27 or 0x3F*

### 7. Push Button (Stage Start)

**Button Circuit**
```
Button Pin 1 → Pico GPIO 9 (Pin 12)
Button Pin 2 → GND
Optional: 100nF capacitor across button for debounce
```
*Internal pull-up enabled in software*

### 8. Buzzer (Confirmation Beep)

**Active Buzzer**
```
+ → Pico GPIO 10 (Pin 14)
- → GND
```

**Passive Buzzer (with transistor driver)**
```
Pico GPIO 10 → 1kΩ Resistor → Transistor Base
Transistor Emitter → GND
Transistor Collector → Buzzer (-)
Buzzer (+) → 5V
```

### 9. UV LED (Reward Light)

**UV LED Circuit**
```
Pico GPIO 11 (Pin 15) → 220Ω Resistor → UV LED Anode (+)
UV LED Cathode (-) → GND
```

*Or use relay/transistor for higher power UV light*

## Complete Pico W Pinout Reference

```
Pico W Pinout (Left Side)
═══════════════════════════════
Pin 1  (GPIO 0)  → I2C0 SDA (LCD)
Pin 2  (GPIO 1)  → I2C0 SCL (LCD)
Pin 3  (GND)     → Ground
Pin 4  (GPIO 2)  → X Motor PWM
Pin 5  (GPIO 3)  → X Motor DIR
Pin 6  (GPIO 4)  → Y Motor PWM
Pin 7  (GPIO 5)  → Y Motor DIR
Pin 8  (GND)     → Ground
Pin 9  (GPIO 6)  → X Limit Switch
Pin 10 (GPIO 7)  → Y Limit Switch
Pin 11 (GPIO 8)  → Electromagnet
Pin 12 (GPIO 9)  → Push Button
Pin 13 (GND)     → Ground
Pin 14 (GPIO 10) → Buzzer
Pin 15 (GPIO 11) → UV LED
Pin 16 (GPIO 12) → (Reserved)
Pin 17 (GPIO 13) → (Reserved)
Pin 18 (GND)     → Ground
Pin 19 (GPIO 14) → (Reserved)
Pin 20 (GPIO 15) → (Reserved)

Pico W Pinout (Right Side)
═══════════════════════════════
Pin 40 (VBUS)    → 5V Input
Pin 39 (VSYS)    → 5V Input
Pin 38 (GND)     → Ground
Pin 37 (3V3_EN)  → 3.3V Enable
Pin 36 (3V3_OUT) → 3.3V Output → Pots
Pin 35 (ADC_VREF)→ ADC Reference
Pin 34 (GPIO 28) → (Reserved)
Pin 33 (GND)     → Ground
Pin 32 (GPIO 27) → ADC1 (Y Pot)
Pin 31 (GPIO 26) → ADC0 (X Pot)
Pin 30 (RUN)     → Reset
Pin 29 (GPIO 22) → (WiFi - Reserved)
```

## Motor Driver Wiring (L298N Example)

```
L298N Module Connections
════════════════════════════════════════

Power Input:
  12V   → 12V DC Supply (+)
  GND   → Common Ground
  5V    → 5V Logic Supply (if jumper removed)

Motor A (X-Axis):
  OUT1  → X Motor Wire 1
  OUT2  → X Motor Wire 2
  ENA   → Pico GPIO 2 (PWM)
  IN1   → Pico GPIO 3 (Direction)
  IN2   → GND (or GPIO for H-bridge)

Motor B (Y-Axis):
  OUT3  → Y Motor Wire 1
  OUT4  → Y Motor Wire 2
  ENB   → Pico GPIO 4 (PWM)
  IN3   → Pico GPIO 5 (Direction)
  IN4   → GND (or GPIO for H-bridge)

Logic:
  GND   → Common Ground with Pico
```

## Power Supply Requirements

### Voltage Rails Needed
1. **12V DC** (2A minimum) - Motors and electromagnet
2. **5V DC** (2A minimum) - Pico W, LCD, logic circuits
3. **3.3V** - Generated by Pico W for potentiometers

### Power Supply Options

**Option 1: Dual Supply**
```
12V 2A Power Supply → Motors/Electromagnet
5V 2A USB Adapter → Pico W VBUS
```

**Option 2: Single 12V Supply with Buck Converter**
```
12V Supply → Motors/Electromagnet
          └→ Buck Converter (12V→5V) → Pico W VSYS
```

## Safety Considerations

### Flyback Diodes
**Required for inductive loads:**
- Across electromagnet: 1N4007 diode (cathode to +V)
- Across each motor: 1N4007 diode (if not using H-bridge)

### Current Limiting
- UV LED: 220Ω resistor (or as per LED specs)
- Buzzer: May need transistor driver for high current

### Isolation
- Use optocouplers for complete isolation between logic and power circuits (optional but recommended)

### Grounding
- **CRITICAL**: All ground connections must be common
- Use star grounding topology to minimize noise

## Testing Procedure

### 1. Power Test (No Load)
```
1. Connect 5V supply to Pico W
2. Verify 3.3V output on Pin 36
3. Check LED on Pico W lights up
4. Measure voltages at all power pins
```

### 2. I2C LCD Test
```
1. Upload I2C scanner code
2. Verify LCD address detected (0x27 or 0x3F)
3. Test LCD with hello world program
```

### 3. ADC Test (Potentiometers)
```
1. Read ADC values with test program
2. Rotate pots and verify full range (0-4095)
3. Check for stable readings (no noise)
```

### 4. Motor Test
```
1. Test motors individually with simple PWM
2. Verify direction control works
3. Check limit switches interrupt motion
```

### 5. Electromagnet Test
```
1. Test with small metal object
2. Verify pickup strength adequate
3. Check release is clean (no residual magnetism)
```

### 6. Full System Test
```
1. Run homing sequence
2. Test manual control with pots
3. Verify LCD updates in real-time
4. Test complete placement cycle
```

## Cable Management

### Recommended Cable Types
- **Power**: 18-20 AWG for 12V motors
- **Logic**: 22-24 AWG for signals
- **I2C**: Twisted pair, keep < 1 meter
- **Motors**: Shielded cable if near sensors

### Cable Routing
- Keep motor cables away from signal cables
- Use cable ties for strain relief
- Separate power and signal cables where possible

## Troubleshooting Tips

### Motors Run Backwards
- Swap motor wire polarity OR
- Invert direction pin logic in code

### LCD Displays Garbage
- Check I2C address
- Verify 5V supply is stable
- Check SDA/SCL not swapped

### Potentiometers Jittery
- Add capacitor (0.1µF) across pot terminals
- Increase DEADZONE in code
- Check for proper grounding

### Electromagnet Weak
- Verify 12V supply adequate
- Check for voltage drop in wiring
- Ensure transistor/relay fully saturated

---

**Note**: Always double-check connections before applying power. Start with low voltage testing when possible.


old:

# RP2040 Gantry System - Wiring Guide

Complete wiring documentation for the button-controlled dual-motor gantry system.

---

## 📌 Pin Summary

| Component | Pin | GPIO | Physical Pin | Notes |
|-----------|-----|------|--------------|-------|
| **I2C LCD** |
| SDA | GPIO 0 | Pin 1 | I2C Data |
| SCL | GPIO 1 | Pin 2 | I2C Clock |
| **Motor A (Right Motor)** |
| Enable A (PWM) | GPIO 15 | Pin 20 | H-Bridge ENA |
| Input 1 | GPIO 17 | Pin 22 | Direction Control |
| Input 2 | GPIO 16 | Pin 21 | Direction Control |
| **Motor B (Left Motor)** |
| Enable B (PWM) | GPIO 13 | Pin 17 | H-Bridge ENB |

| Input 3 | GPIO 19 | Pin 25 | Direction Control |
| Input 4 | GPIO 18 | Pin 24 | Direction Control |
| **Control Buttons** |
| Forward | GPIO 6 | Pin 9 | Y+ Movement |
| Right | GPIO 7 | Pin 10 | X+ Movement |
| Left | GPIO 8 | Pin 11 | X- Movement |
| Back | GPIO 9 | Pin 12 | Y- Movement |

---

## 🔌 Detailed Wiring

### I2C LCD Display (16x2 with PCF8574 Backpack)

```
LCD Module → RP2040 Pico
─────────────────────────
VCC        → 3.3V or 5V (check your module)
GND        → GND
SDA        → GPIO 0 (Pin 1)
SCL        → GPIO 1 (Pin 2)

I2C Address: 0x27
I2C Speed: 100kHz
```

**Note:** GPIO 0 and 1 have internal pull-up resistors enabled in code.

---

### Motor A - Right Motor (H-Bridge Channel A)

```
H-Bridge → RP2040 Pico
──────────────────────
ENA (Enable A) → GPIO 15 (Pin 20) - PWM Signal
IN1            → GPIO 17 (Pin 22) - Direction
IN2            → GPIO 16 (Pin 21) - Direction

Motor Wiring:
OUT1 → Motor A Terminal 1
OUT2 → Motor A Terminal 2
```

**Direction Control:**
- Forward: IN1=HIGH, IN2=LOW
- Backward: IN1=LOW, IN2=HIGH
- Stop: IN1=LOW, IN2=LOW, PWM=0

---

### Motor B - Left Motor (H-Bridge Channel B)

```
H-Bridge → RP2040 Pico
──────────────────────
ENB (Enable B) → GPIO 13 (Pin 17) - PWM Signal
IN3            → GPIO 19 (Pin 25) - Direction
IN4            → GPIO 18 (Pin 24) - Direction

Motor Wiring:
OUT3 → Motor B Terminal 1
OUT4 → Motor B Terminal 2
```

**Direction Control:**
- Forward: IN3=HIGH, IN4=LOW
- Backward: IN3=LOW, IN4=HIGH
- Stop: IN3=LOW, IN4=LOW, PWM=0

---

### Control Buttons

All buttons use **pull-down resistors** configured in software.

```
Button Wiring (Active HIGH):
────────────────────────────

Forward Button:
  One terminal → GPIO 6 (Pin 9)
  Other terminal → 3.3V

Right Button:
  One terminal → GPIO 7 (Pin 10)
  Other terminal → 3.3V

Left Button:
  One terminal → GPIO 8 (Pin 11)
  Other terminal → 3.3V

Back Button:
  One terminal → GPIO 9 (Pin 12)
  Other terminal → 3.3V
```

**Button Logic:**
- Unpressed: GPIO reads LOW (0) - pull-down to GND
- Pressed: GPIO reads HIGH (1) - connected to 3.3V

---

## 🎮 Movement Control

| Button | X-Axis | Y-Axis | Motor A | Motor B |
|--------|--------|--------|---------|---------|
| **Forward** | - | + | Forward | Backward |
| **Back** | - | - | Backward | Forward |
| **Right** | + | - | Forward | Forward |
| **Left** | - | - | Backward | Backward |

**Speed:** All movements run at PWM level 10000 (~15% of maximum)

---

## ⚡ Power Requirements

### RP2040 Pico
- **Input:** 5V via USB or VSYS
- **Logic Level:** 3.3V

### H-Bridge Motor Driver (L298N or similar)
- **Motor Power (VCC):** 12V DC (for 12V motors)
- **Logic Power (5V):** Can be powered from Pico's VBUS or separate 5V supply
- **GND:** Common ground with Pico **CRITICAL**

### Motors
- **Type:** 12V DC motors
- **Current:** Check motor specs and ensure H-bridge can handle load

---

## 🔧 H-Bridge Connections

```
L298N Module Connections:
─────────────────────────

Power:
  12V    → External 12V power supply (+)
  GND    → Common ground (Pico GND + 12V supply GND)
  5V     → Pico VBUS (or leave jumper if using onboard regulator)

Motor A (Right):
  OUT1   → Motor A Wire 1
  OUT2   → Motor A Wire 2

Motor B (Left):
  OUT3   → Motor B Wire 1
  OUT4   → Motor B Wire 2

Control (to Pico):
  ENA    → GPIO 15 (PWM)
  IN1    → GPIO 17
  IN2    → GPIO 16
  ENB    → GPIO 13 (PWM)
  IN3    → GPIO 19
  IN4    → GPIO 18
```

---

## ✅ Initialization Sequence

On startup, the gantry performs an automatic initialization:

1. **Display:** "Moving Away From Limits..."
2. **Back Movement:** 1.5 seconds (clears Y-axis limit)
3. **Left Movement:** 1.5 seconds (clears X-axis limit)
4. **Stop:** Motors halt
5. **Ready:** Display shows "Ready!" and awaits button input

---

## 🐛 Troubleshooting

### LCD Not Displaying
- Check I2C address (run I2C scanner if needed)
- Verify SDA/SCL connections
- Check power to LCD module

### Motors Not Running
- Verify common ground between Pico and H-bridge
- Check 12V power supply to H-bridge
- Test motor connections directly to 12V

### Buttons Not Responding
- Verify button connections to correct GPIO pins
- Check 3.3V supply to button terminals
- LCD should show button states: `F:0 R:0 / L:0 B:0`

### Erratic Movement
- Check for loose motor connections
- Verify PWM enable pins are connected
- Ensure adequate power supply current capacity

---

## 📝 Notes

- **Debouncing:** Implemented in software (double-read with 100μs delay)
- **Update Rate:** 20ms loop cycle
- **PWM Frequency:** Default RP2040 PWM (based on 125MHz clock / 65535 wrap)
- **Pull Resistors:** All buttons use internal pull-down resistors

---

## 🔗 Related Files

- `Embedded2.c` - Main firmware source code
- `CMakeLists.txt` - Build configuration
- `build/Embedded2.uf2` - Compiled firmware (drag to RPI-RP2 drive)

---

**Last Updated:** December 2025  
**Hardware:** Raspberry Pi Pico (RP2040)  
**SDK Version:** Pico SDK 2.2.0
