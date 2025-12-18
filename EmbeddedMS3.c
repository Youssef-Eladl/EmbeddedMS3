/**
 * Forge Registry Station - Aruco Plate Positioning System
 * Manual Gantry Control with Real-time Camera Feedback
 * Pico with USB Serial Camera Input, Dual-Pot H-Bot Motion, LCD, and Electromagn et
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <stdarg.h>
#include "pico/stdlib.h"
#include "hardware/adc.h"
#include "hardware/pwm.h"
#include "hardware/i2c.h"


// ============================================================================
// PIN DEFINITIONS
// ============================================================================

// Potentiometers (Analog inputs for ADC)
#define POT_X_PIN       26  // ADC0 - X-axis control
#define POT_Y_PIN       27  // ADC1 - Y-axis control

// DC Motor Outputs (L298N style: PWM enable + dual direction pins)
#define MOTOR_A_PWM     15  // Motor A PWM (ENA)
#define MOTOR_A_IN1     13  // Motor A direction input 1
#define MOTOR_A_IN2     12  // Motor A direction input 2
#define MOTOR_B_PWM     14  // Motor B PWM (ENB)
#define MOTOR_B_IN3     11  // Motor B direction input 3
#define MOTOR_B_IN4     10  // Motor B direction input 4

// Limit Switches (for homing)
#define LIMIT_X_PIN     21   // X-axis limit switch (emergency stop)
#define LIMIT_Y_PIN     20   // Y-axis limit switch (emergency stop)

// Electromagnet H-Bridge Control
#define EM_ENABLE_PIN   2   // H-bridge enable (PWM capable)
#define EM_IN1_PIN      19  // H-bridge IN1 (polarity control)
#define EM_IN2_PIN      18   // H-bridge IN2 (polarity control)

// Push Button
#define BUTTON_PIN      6   // Stage start button (unused)

// Buzzer
#define BUZZER_PIN      9  // Confirmation buzzer

// UV LED
#define UV_LED_PIN      8  // Reward UV LED

// LCD I2C (Uses I2C0)
#define I2C_SDA_PIN     16   // I2C0 SDA
#define I2C_SCL_PIN     17   // I2C0 SCL
#define LCD_ADDR        0x27 // Common I2C LCD address (or 0x3F)

// ============================================================================
// CONSTANTS
// ============================================================================

#define GRID_SIZE           5
#define ADC_MAX             4095    // 12-bit ADC
#define DEADZONE            600     // Potentiometer deadzone (larger for stability)
#define PWM_MAX             65535   // 16-bit PWM
#define PLACEMENT_TIME      5000    // 5 seconds in milliseconds
#define BUTTON_DEBOUNCE     50      // Button debounce time (ms)
#define TEST_DISPLAY_ONLY   0      // Set to 1 to disable motor movement and show commands on LCD
#define ADC_SAMPLES         16      // Number of samples to average (increased for stability)
#define SMOOTHING_FACTOR    0.3f    // Exponential smoothing (0.0-1.0, lower = smoother)

// ============================================================================
// STATE MACHINE
// ============================================================================

typedef enum {
    STATE_INIT,
    STATE_HOMING,
    STATE_WAIT_PLATE_1,
    STATE_PICK_PLATE_1,
    STATE_MOVE_PLATE_1,
    STATE_VERIFY_PLATE_1,
    STATE_WAIT_PLATE_2,
    STATE_PICK_PLATE_2,
    STATE_MOVE_PLATE_2,
    STATE_VERIFY_PLATE_2,
    STATE_COMPLETE
} system_state_t;

// ============================================================================
// DATA STRUCTURES
// ============================================================================

typedef struct {
    int id;
    int grid_row;
    int grid_col;
    int center_x;
    int center_y;
    float area;
    bool valid;
} aruco_marker_t;

typedef struct {
    int target_x;
    int target_y;
    bool placed;
} aruco_plate_t;

typedef struct {
    int current_x;
    int current_y;
    aruco_marker_t detected_marker;
    bool marker_detected;
    uint32_t last_update_time;
} camera_data_t;

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

static system_state_t current_state = STATE_INIT;
static camera_data_t camera_data = {0};
static aruco_plate_t plate_1 = {0};
static aruco_plate_t plate_2 = {0};
static uint32_t placement_start_time = 0;
static bool magnet_active = false;
static int qr_sequence[4] = {2, 5, 4, 3}; // Format matches camera "5234": {col1, row1, col2, row2} -> (5,2) and (3,4) in 1-indexed
static int16_t debug_motor_a = 0;
static int16_t debug_motor_b = 0;
static uint16_t debug_adc_x = 0;
static uint16_t debug_adc_y = 0;
static int16_t debug_x_cmd = 0;
static int16_t debug_y_cmd = 0;
// Smoothed values for exponential filtering
static float smoothed_x = 0.0f;
static float smoothed_y = 0.0f;
static bool smoothing_initialized = false;
static bool waiting_for_confirmation = false;

// ============================================================================
// LCD I2C FUNCTIONS (16x2 LCD)
// ============================================================================

void lcd_send_byte(uint8_t val, int mode) {
    uint8_t high = (val & 0xF0) | mode | 0x08; // RS + backlight
    uint8_t low = ((val << 4) & 0xF0) | mode | 0x08;
    
    uint8_t data[4] = {high | 0x04, high, low | 0x04, low}; // Pulse enable high then low
    i2c_write_blocking(i2c0, LCD_ADDR, data, 4, false);
    sleep_us(50); // LCD needs time to process
}

void lcd_send_cmd(uint8_t cmd) {
    lcd_send_byte(cmd, 0);
}

void lcd_send_char(char c) {
    lcd_send_byte(c, 1);
}

void lcd_init(void) {
    i2c_init(i2c0, 100 * 1000); // 100kHz
    gpio_set_function(I2C_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(I2C_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(I2C_SDA_PIN);
    gpio_pull_up(I2C_SCL_PIN);
    
    sleep_ms(50); // Wait for LCD power-on (>40ms required)
    
    // Send 0x03 three times for 8-bit mode init (HD44780 standard sequence)
    lcd_send_cmd(0x03);
    sleep_ms(5);
    lcd_send_cmd(0x03);
    sleep_us(150);
    lcd_send_cmd(0x03);
    sleep_us(150);
    
    lcd_send_cmd(0x02); // Switch to 4-bit mode
    sleep_us(150);
    
    lcd_send_cmd(0x28); // 4-bit mode, 2 lines, 5x8 font
    sleep_us(50);
    lcd_send_cmd(0x0C); // Display on, cursor off, blink off
    sleep_us(50);
    lcd_send_cmd(0x06); // Entry mode: increment cursor, no display shift
    sleep_us(50);
    lcd_send_cmd(0x01); // Clear display
    sleep_ms(2); // Clear needs 1.5ms
}

void lcd_clear(void) {
    lcd_send_cmd(0x01);
    sleep_ms(2);
}

void lcd_set_cursor(int col, int row) {
    int row_offsets[] = {0x00, 0x40};
    lcd_send_cmd(0x80 | (col + row_offsets[row]));
}

void lcd_print(const char *str) {
    while (*str) {
        lcd_send_char(*str++);
    }
}

void lcd_printf(int col, int row, const char *format, ...) {
    char buffer[17]; // 16 chars + null terminator
    va_list args;
    va_start(args, format);
    vsnprintf(buffer, sizeof(buffer), format, args);
    va_end(args);
    
    lcd_set_cursor(col, row);
    lcd_print(buffer);
}

// ----------------------------------------------------------------------------
// UNIFIED LCD UPDATE
// ----------------------------------------------------------------------------
// Single function to update LCD based on current state
// Called from main loop with throttling, or forced on state changes
static uint32_t last_lcd_refresh_ms = 0;
static const uint32_t LCD_REFRESH_INTERVAL_MS = 100;  // Update at 10Hz for responsive position display

// Forward declaration for state machine
void update_lcd_for_state(void);

static void update_lcd_impl(bool force) {
    uint32_t now = to_ms_since_boot(get_absolute_time());
    
    // Throttle updates to reduce flicker (unless forced)
    if (!force && (now - last_lcd_refresh_ms < LCD_REFRESH_INTERVAL_MS)) {
        return;
    }
    last_lcd_refresh_ms = now;
    
    lcd_clear();
    
    switch (current_state) {
        case STATE_INIT:
            lcd_printf(0, 0, "INITIALIZING...");
            break;
            
        case STATE_HOMING:
            // Homing has its own LCD messages in homing_sequence()
            break;
            
        case STATE_WAIT_PLATE_1:
            if (waiting_for_confirmation) {
                lcd_printf(0, 0, "ARUCO DETECTED");
                lcd_printf(0, 1, "Press button");
            } else {
                lcd_printf(0, 0, "PLACE ARUCO");
                lcd_printf(0, 1, "at (1,1)");
            }
            break;
            
        case STATE_PICK_PLATE_1:
            lcd_printf(0, 0, "ID %d DETECTED", camera_data.detected_marker.id);
            lcd_printf(0, 1, "T:%d,%d PICK", 
                      plate_1.target_y + 1, plate_1.target_x + 1);
            break;
            
        case STATE_MOVE_PLATE_1:
        case STATE_VERIFY_PLATE_1:
            lcd_printf(0, 0, "T:%d,%d  C:%d,%d", 
                      plate_1.target_y + 1, plate_1.target_x + 1,
                      camera_data.current_y + 1, camera_data.current_x + 1);
            lcd_printf(0, 1, "Plate 1 %s", 
                      current_state == STATE_MOVE_PLATE_1 ? "Moving" : "Verify");
            break;
            
        case STATE_WAIT_PLATE_2:
            if (waiting_for_confirmation) {
                lcd_printf(0, 0, "ARUCO DETECTED");
                lcd_printf(0, 1, "Press button");
            } else {
                lcd_printf(0, 0, "ADD ARUCO #2");
                lcd_printf(0, 1, "at (1,1)");
            }
            break;
            
        case STATE_PICK_PLATE_2:
            lcd_printf(0, 0, "ID %d DETECTED", camera_data.detected_marker.id);
            lcd_printf(0, 1, "T:%d,%d PICK", 
                      plate_2.target_y + 1, plate_2.target_x + 1);
            break;
            
        case STATE_MOVE_PLATE_2:
        case STATE_VERIFY_PLATE_2:
            lcd_printf(0, 0, "T:%d,%d  C:%d,%d", 
                      plate_2.target_y + 1, plate_2.target_x + 1,
                      camera_data.current_y + 1, camera_data.current_x + 1);
            lcd_printf(0, 1, "Plate 2 %s", 
                      current_state == STATE_MOVE_PLATE_2 ? "Moving" : "Verify");
            break;
            
        case STATE_COMPLETE:
            lcd_printf(0, 0, "** SUCCESS! **");
            lcd_printf(0, 1, "UV LIGHT ON");
            break;
            
        default:
            break;
    }
}

// Called from state machine on state changes - forces immediate update
void update_lcd_for_state(void) {
    update_lcd_impl(true);
}

// Called from main loop - throttled to 5Hz
void update_lcd_periodic(void) {
    update_lcd_impl(false);
}

// ============================================================================
// MOTOR CONTROL FUNCTIONS
// ============================================================================

void motors_init(void) {
    // Initialize PWM for motors
    gpio_set_function(MOTOR_A_PWM, GPIO_FUNC_PWM);
    gpio_set_function(MOTOR_B_PWM, GPIO_FUNC_PWM);
    
    uint slice_a = pwm_gpio_to_slice_num(MOTOR_A_PWM);
    uint slice_b = pwm_gpio_to_slice_num(MOTOR_B_PWM);
    
    pwm_set_wrap(slice_a, PWM_MAX);
    pwm_set_wrap(slice_b, PWM_MAX);
    pwm_set_enabled(slice_a, true);
    pwm_set_enabled(slice_b, true);
    
    // Initialize direction pins
    gpio_init(MOTOR_A_IN1);
    gpio_set_dir(MOTOR_A_IN1, GPIO_OUT);
    gpio_init(MOTOR_A_IN2);
    gpio_set_dir(MOTOR_A_IN2, GPIO_OUT);
    gpio_init(MOTOR_B_IN3);
    gpio_set_dir(MOTOR_B_IN3, GPIO_OUT);
    gpio_init(MOTOR_B_IN4);
    gpio_set_dir(MOTOR_B_IN4, GPIO_OUT);
}

void motor_set_l298(uint gpio_pwm, uint gpio_in1, uint gpio_in2, int speed) {
    // speed: -255 to +255 (negative = reverse)
    if (speed == 0) {
        // Hard stop / brake: both LOW, PWM=0
        gpio_put(gpio_in1, 0);
        gpio_put(gpio_in2, 0);
        pwm_set_gpio_level(gpio_pwm, 0);
        return;
    }

    bool forward = speed > 0;
    uint16_t pwm_value = (abs(speed) * PWM_MAX) / 255;

    gpio_put(gpio_in1, forward ? 1 : 0);
    gpio_put(gpio_in2, forward ? 0 : 1);
    pwm_set_gpio_level(gpio_pwm, pwm_value);
}

void motors_stop(void) {
    motor_set_l298(MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2, 0);
    motor_set_l298(MOTOR_B_PWM, MOTOR_B_IN3, MOTOR_B_IN4, 0);
}

// ============================================================================
// POTENTIOMETER CONTROL WITH H-BOT MAPPING
// ============================================================================

static void hbot_drive(int x_cmd, int y_cmd);
bool check_emergency_stop(void); // Forward declaration for emergency stop

const char* get_direction_str(int motor_a, int motor_b) {
    int threshold = 20; // Minimum value to register movement
    
    if (abs(motor_a) < threshold && abs(motor_b) < threshold) {
        return "STOP";
    }
    
    // Check primary directions
    if (motor_a > threshold && motor_b > threshold) {
        if (abs(motor_a - motor_b) < threshold) return "RIGHT";
        if (motor_a > motor_b) return "RIGHT-UP";
        return "RIGHT-DN";
    }
    if (motor_a < -threshold && motor_b < -threshold) {
        if (abs(motor_a - motor_b) < threshold) return "LEFT";
        if (motor_a < motor_b) return "LEFT-UP";
        return "LEFT-DN";
    }
    if (motor_a > threshold && motor_b < -threshold) {
        if (abs(motor_a + motor_b) < threshold) return "UP";
        if (motor_a > abs(motor_b)) return "RIGHT-UP";
        return "UP-LEFT";
    }
    if (motor_a < -threshold && motor_b > threshold) {
        if (abs(motor_a + motor_b) < threshold) return "DOWN";
        if (abs(motor_a) > motor_b) return "LEFT-DN";
        return "DOWN-RT";
    }
    
    // Edge cases
    if (motor_a > threshold) return "RIGHT-UP";
    if (motor_a < -threshold) return "LEFT-DN";
    if (motor_b > threshold) return "DOWN";
    if (motor_b < -threshold) return "UP";
    
    return "STOP";
}

void adc_init_all(void) {
    adc_init();
    adc_gpio_init(POT_X_PIN);
    adc_gpio_init(POT_Y_PIN);
}

static int read_pot_with_deadzone(uint adc_channel) {
    // Average more readings to reduce noise
    uint32_t sum = 0;
    for (int i = 0; i < ADC_SAMPLES; i++) {
        adc_select_input(adc_channel);
        sum += adc_read();
        sleep_us(10);
    }
    float raw = (float)(sum / ADC_SAMPLES);
    
    // Apply exponential smoothing to reduce jitter
    float *smoothed = (adc_channel == 0) ? &smoothed_x : &smoothed_y;
    if (!smoothing_initialized) {
        *smoothed = raw;
        if (adc_channel == 1) smoothing_initialized = true;  // Initialize on second channel
    } else {
        *smoothed = (*smoothed * (1.0f - SMOOTHING_FACTOR)) + (raw * SMOOTHING_FACTOR);
    }
    
    int smoothed_int = (int)(*smoothed);
    int mid = ADC_MAX / 2;          // ~2047 corresponds to 1.65V (3.3V/2)
    int centered = smoothed_int - mid;        // negative below 1.65V, positive above

    // Deadzone around center
    if (abs(centered) < DEADZONE) {
        return 0;
    }

    // Normalize to -1..+1 using 1.65V span
    float norm = (float)centered / (float)mid;
    
    // Apply quadratic scaling: speed increases with square of distance from center
    // This gives fine control near center and faster movement at extremes
    float sign = (norm >= 0) ? 1.0f : -1.0f;
    float magnitude = fabs(norm);
    float scaled = sign * magnitude * magnitude * 255.0f;
    
    if (scaled > 255.0f) scaled = 255.0f;
    if (scaled < -255.0f) scaled = -255.0f;
    return (int)scaled;
}

static void update_motors_from_pots_hbot(void) {
    // Read potentiometers with filtering (this already does averaging internally)
    int x_cmd = read_pot_with_deadzone(0); // ADC0 -> X axis
    int y_cmd = read_pot_with_deadzone(1); // ADC1 -> Y axis
    
    // Store raw values for debugging (use smoothed values)
    debug_adc_x = (uint16_t)smoothed_x;
    debug_adc_y = (uint16_t)smoothed_y;
    debug_x_cmd = x_cmd;
    debug_y_cmd = y_cmd;
    
    hbot_drive(x_cmd, y_cmd);
}

// Forward declaration
uint8_t check_limit_switches(void);

static void hbot_drive(int x_cmd, int y_cmd) {
    // Check which limit switches are active
    uint8_t limits = check_limit_switches();
    bool x_limit = (limits & 0x01) != 0;  // LIMIT_X_PIN (bit 0) - DOWN limit
    bool y_limit = (limits & 0x02) != 0;  // LIMIT_Y_PIN (bit 1) - LEFT limit
    
    // Constrain commands based on active limits (matching homing sequence behavior)
    // LIMIT_Y_PIN hit: prevent further LEFT movement (negative X)
    if (y_limit && x_cmd < 0) {
        x_cmd = 0;
    }
    
    // LIMIT_X_PIN hit: prevent further DOWN movement (positive Y)
    if (x_limit && y_cmd > 0) {
        y_cmd = 0;
    }
    
    // H-bot mapping:
    //  - Pure X: both motors same direction (neg X => both CCW)
    //  - Pure Y: motors opposite directions
    int motor_a = x_cmd + y_cmd;
    int motor_b = x_cmd - y_cmd;

    // Clamp combined commands to valid range
    if (motor_a > 255) motor_a = 255;
    if (motor_a < -255) motor_a = -255;
    if (motor_b > 255) motor_b = 255;
    if (motor_b < -255) motor_b = -255;

    debug_motor_a = (int16_t)motor_a;
    debug_motor_b = (int16_t)motor_b;

    if (TEST_DISPLAY_ONLY) {
        motors_stop(); // Hard stop: inputs low, PWM=0
        return;
    }
    
    // Normal operation - drive motors
    motor_set_l298(MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2, motor_a);
    motor_set_l298(MOTOR_B_PWM, MOTOR_B_IN3, MOTOR_B_IN4, motor_b);
}

// ============================================================================
// HOMING FUNCTIONS
// ============================================================================

void homing_init(void) {
    gpio_init(LIMIT_X_PIN);
    gpio_set_dir(LIMIT_X_PIN, GPIO_IN);
    gpio_pull_down(LIMIT_X_PIN); // Pull-down for active-high switch
    
    gpio_init(LIMIT_Y_PIN);
    gpio_set_dir(LIMIT_Y_PIN, GPIO_IN);
    gpio_pull_down(LIMIT_Y_PIN); // Pull-down for active-high switch
}

// Check limit switches - returns bitmask: bit 0 = X limit, bit 1 = Y limit
// Does NOT automatically stop motors - caller must handle constraints
uint8_t check_limit_switches(void) {
    uint8_t limits = 0;
    if (gpio_get(LIMIT_X_PIN)) limits |= 0x01;  // X limit active
    if (gpio_get(LIMIT_Y_PIN)) limits |= 0x02;  // Y limit active
    return limits;
}

// Legacy emergency stop - returns true if either limit switch is triggered
// Used during homing sequence where we want full stops
bool check_emergency_stop(void) {
    uint8_t limits = check_limit_switches();
    if (limits != 0) {
        motors_stop();
        return true;
    }
    return false;
}

bool homing_sequence(void) {
    // PHASE 1: Home X-axis
    lcd_clear();
    lcd_printf(0, 0, "HOMING X...");
    lcd_printf(1, 0, "Moving left");
    
    // Move in X direction until Y limit switch triggered (active HIGH)
    while (!gpio_get(LIMIT_Y_PIN)) {
        motor_set_l298(MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2, -100);
        motor_set_l298(MOTOR_B_PWM, MOTOR_B_IN3, MOTOR_B_IN4, -100);
        sleep_ms(10);
    }
    motors_stop();
    sleep_ms(500);
    
    printf("X-axis homed (limit switch triggered)\n");
    
    // PHASE 2: Home Y-axis
    lcd_clear();
    lcd_printf(0, 0, "HOMING Y...");
    lcd_printf(1, 0, "Moving down");
    
    // Move in Y direction until X limit switch triggered (active HIGH)
    while (!gpio_get(LIMIT_X_PIN)) {
        motor_set_l298(MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2, 100);
        motor_set_l298(MOTOR_B_PWM, MOTOR_B_IN3, MOTOR_B_IN4, -100);
        sleep_ms(10);
    }
    motors_stop();
    
    printf("Y-axis homed (limit switch triggered)\n");
    
    camera_data.current_x = 0;
    camera_data.current_y = 0;
    
    lcd_clear();
    lcd_printf(0, 0, "HOMING COMPLETE");
    lcd_printf(1, 0, "X=0 Y=0");
    sleep_ms(1000);
    
    return true;
}

// ============================================================================
// ELECTROMAGNET & BUZZER
// ============================================================================

void magnet_init(void) {
    gpio_init(EM_ENABLE_PIN);
    gpio_set_dir(EM_ENABLE_PIN, GPIO_OUT);
    gpio_put(EM_ENABLE_PIN, 0);
    
    gpio_init(EM_IN1_PIN);
    gpio_set_dir(EM_IN1_PIN, GPIO_OUT);
    gpio_put(EM_IN1_PIN, 0);
    
    gpio_init(EM_IN2_PIN);
    gpio_set_dir(EM_IN2_PIN, GPIO_OUT);
    gpio_put(EM_IN2_PIN, 0);
}

void magnet_set(bool active) {
    if (active) {
        // Turn on electromagnet with forward polarity
        gpio_put(EM_IN1_PIN, 1);
        gpio_put(EM_IN2_PIN, 0);
        gpio_put(EM_ENABLE_PIN, 1);
    } else {
        // Just turn off (no reverse)
        gpio_put(EM_ENABLE_PIN, 0);
        gpio_put(EM_IN1_PIN, 0);
        gpio_put(EM_IN2_PIN, 0);
    }
    magnet_active = active;
}

void magnet_release_hold(void) {
    // Reverse polarity and KEEP it running until next pickup
    // This helps repel the plate and demagnetize
    gpio_put(EM_IN1_PIN, 0);
    gpio_put(EM_IN2_PIN, 1);
    gpio_put(EM_ENABLE_PIN, 1);
    magnet_active = false;  // Logically released
    printf("Magnet: Reverse polarity (holding)\n");
}

void magnet_release_final(void) {
    // Reverse polarity for 1 second, then turn off completely
    gpio_put(EM_IN1_PIN, 0);
    gpio_put(EM_IN2_PIN, 1);
    gpio_put(EM_ENABLE_PIN, 1);
    printf("Magnet: Reverse polarity (1 second)\n");
    sleep_ms(1000);  // 1 second reverse pulse
    gpio_put(EM_ENABLE_PIN, 0);
    gpio_put(EM_IN1_PIN, 0);
    gpio_put(EM_IN2_PIN, 0);
    magnet_active = false;
    printf("Magnet: OFF\n");
}

void buzzer_init(void) {
    gpio_init(BUZZER_PIN);
    gpio_set_dir(BUZZER_PIN, GPIO_OUT);
}

void buzzer_beep(int duration_ms) {
    gpio_put(BUZZER_PIN, 1);
    sleep_ms(duration_ms);
    gpio_put(BUZZER_PIN, 0);
}

void uv_led_init(void) {
    gpio_init(UV_LED_PIN);
    gpio_set_dir(UV_LED_PIN, GPIO_OUT);
    gpio_put(UV_LED_PIN, 0);
}

void uv_led_set(bool on) {
    gpio_put(UV_LED_PIN, on);
}

// ============================================================================
// BUTTON HANDLER
// ============================================================================

void button_init(void) {
    gpio_init(BUTTON_PIN);
    gpio_set_dir(BUTTON_PIN, GPIO_IN);
    gpio_pull_up(BUTTON_PIN);
}

bool button_check(void) {
    static uint32_t last_press = 0;
    static bool last_state = false;
    
    bool current_state = !gpio_get(BUTTON_PIN); // Active low
    
    if (current_state && !last_state) {
        if (to_ms_since_boot(get_absolute_time()) - last_press > BUTTON_DEBOUNCE) {
            last_press = to_ms_since_boot(get_absolute_time());
            last_state = current_state;
            return true;
        }
    }
    
    last_state = current_state;
    return false;
}


// ============================================================================
// USB SERIAL PARSING (Camera → Pico)
// ============================================================================

static char serial_buffer[128];
static uint8_t serial_idx = 0;

void handle_serial_line(const char *line) {
    // Check for PICKUP command: PICKUP,id,target_row,target_col
    if (strncmp(line, "PICKUP,", 7) == 0) {
        int id = 0, target_row = 0, target_col = 0;
        if (sscanf(line, "PICKUP,%d,%d,%d", &id, &target_row, &target_col) == 3) {
            printf("SER RX -> PICKUP command: ID=%d, Target=(%d,%d)\n", id, target_row+1, target_col+1);
            
            // Update plate target based on current state
            if (current_state == STATE_WAIT_PLATE_1 || current_state == STATE_PICK_PLATE_1) {
                plate_1.target_x = target_col;  // Note: target_col is X, target_row is Y in grid
                plate_1.target_y = target_row;
                printf("Plate 1 target updated: (%d,%d)\n", target_col+1, target_row+1);
            } else if (current_state == STATE_WAIT_PLATE_2 || current_state == STATE_PICK_PLATE_2) {
                plate_2.target_x = target_col;
                plate_2.target_y = target_row;
                printf("Plate 2 target updated: (%d,%d)\n", target_col+1, target_row+1);
            }
        }
        return;
    }
    
    // Check for RELEASE command
    if (strncmp(line, "RELEASE", 7) == 0) {
        printf("SER RX -> RELEASE command received\n");
        
        // Transition to next state based on current state
        if (current_state == STATE_VERIFY_PLATE_1 || current_state == STATE_MOVE_PLATE_1) {
            magnet_release_hold();  // Reverse polarity, keep running until next pickup
            plate_1.placed = true;
            current_state = STATE_WAIT_PLATE_2;
            camera_data.marker_detected = false;  // Reset for next marker
            placement_start_time = 0;
            motors_stop();
            buzzer_beep(500);
            update_lcd_for_state();
            printf("Transitioning to WAIT_PLATE_2\n");
        } else if (current_state == STATE_VERIFY_PLATE_2 || current_state == STATE_MOVE_PLATE_2) {
            magnet_release_final();  // Reverse for 1 second, then off
            plate_2.placed = true;
            current_state = STATE_COMPLETE;
            camera_data.marker_detected = false;
            placement_start_time = 0;
            motors_stop();
            buzzer_beep(500);
            update_lcd_for_state();
            printf("Transitioning to COMPLETE\n");
        }
        return;
    }
    
    // Expected format: id,row,col (all ints, 0-indexed)
    int id = 0, row = 0, col = 0;
    if (sscanf(line, "%d,%d,%d", &id, &row, &col) == 3) {
        camera_data.detected_marker.id = id;
        camera_data.detected_marker.grid_row = row;
        camera_data.detected_marker.grid_col = col;
        camera_data.detected_marker.valid = true;
        camera_data.marker_detected = true;
        camera_data.current_x = col;
        camera_data.current_y = row;
        camera_data.last_update_time = to_ms_since_boot(get_absolute_time());
        printf("SER RX -> ID:%d ROW:%d COL:%d\n", id, row, col);
        // LCD update handled by unified update_lcd() in main loop
    }
}

void poll_serial(void) {
    while (true) {
        int ch = getchar_timeout_us(0);
        if (ch == PICO_ERROR_TIMEOUT) {
            break;
        }
        if (ch == '\r') {
            continue;
        }
        if (ch == '\n') {
            serial_buffer[serial_idx] = '\0';
            handle_serial_line(serial_buffer);
            serial_idx = 0;
        } else if (serial_idx < sizeof(serial_buffer) - 1) {
            serial_buffer[serial_idx++] = (char)ch;
        } else {
            serial_idx = 0; // overflow, reset
        }
    }
}

// ============================================================================
// COORDINATE INITIALIZATION FROM QR CODE
// ============================================================================

void init_targets_from_qr(void) {
    // QR sequence format: [col1, row1, col2, row2] (1-indexed)
    // Example "5234": col1=2, row1=5, col2=4, row2=3
    // Gives: Plate 1 -> (5,2) and Plate 2 -> (3,4) in 1-indexed
    
    plate_1.target_x = qr_sequence[0] - 1; // col (X) - convert to 0-based
    plate_1.target_y = qr_sequence[1] - 1; // row (Y) - convert to 0-based
    plate_1.placed = false;
    
    plate_2.target_x = qr_sequence[2] - 1; // col (X) - convert to 0-based
    plate_2.target_y = qr_sequence[3] - 1; // row (Y) - convert to 0-based
    plate_2.placed = false;
    
    printf("Target 1: (%d,%d)\n", plate_1.target_y + 1, plate_1.target_x + 1); // Display as (row,col)
    printf("Target 2: (%d,%d)\n", plate_2.target_y + 1, plate_2.target_x + 1); // Display as (row,col)
}

// ============================================================================
// STATE MACHINE LOGIC
// ============================================================================

bool check_target_reached(int target_x, int target_y) {
    return (camera_data.current_x == target_x && 
            camera_data.current_y == target_y);
}

void state_machine_update(void) {
    static uint32_t state_enter_time = 0;
    uint32_t current_time = to_ms_since_boot(get_absolute_time());
    
    switch (current_state) {
        case STATE_INIT:
            update_lcd_for_state();
            init_targets_from_qr();
            magnet_set(false);  // Ensure magnet is off at startup
            current_state = STATE_HOMING;
            break;
            
        case STATE_HOMING:
            magnet_set(false);  // Keep magnet off during homing
            if (homing_sequence()) {
                current_state = STATE_WAIT_PLATE_1;
                update_lcd_for_state();
            }
            break;
            
        case STATE_WAIT_PLATE_1:
            // Two-step process: detect marker, then wait for button confirmation
            if (camera_data.marker_detected && 
                (camera_data.detected_marker.id == 1 || 
                 camera_data.detected_marker.id == 2) &&
                camera_data.detected_marker.grid_row == 0 &&
                camera_data.detected_marker.grid_col == 0) {
                
                if (!waiting_for_confirmation) {
                    // First time detecting marker - set flag and update LCD
                    waiting_for_confirmation = true;
                    // Determine which plate was detected
                    if (camera_data.detected_marker.id == 1) {
                        // ID 1 goes to target 1
                    } else {
                        // ID 2 goes to target 2 - swap targets
                        int temp_x = plate_1.target_x;
                        int temp_y = plate_1.target_y;
                        plate_1.target_x = plate_2.target_x;
                        plate_1.target_y = plate_2.target_y;
                        plate_2.target_x = temp_x;
                        plate_2.target_y = temp_y;
                    }
                    update_lcd_for_state();
                    buzzer_beep(100);  // Beep to indicate detection
                } else if (button_check()) {
                    // Button pressed - proceed with pickup
                    waiting_for_confirmation = false;
                    current_state = STATE_PICK_PLATE_1;
                    update_lcd_for_state();
                    magnet_set(true);  // Turn on magnet after button confirmation
                    buzzer_beep(200);  // Different beep for confirmation
                }
            } else {
                // Marker not detected or moved - reset confirmation flag
                if (waiting_for_confirmation) {
                    waiting_for_confirmation = false;
                    update_lcd_for_state();
                }
            }
            break;
            
        case STATE_PICK_PLATE_1:
            sleep_ms(1000); // Wait for magnet to grab
            current_state = STATE_MOVE_PLATE_1;
            update_lcd_for_state();
            placement_start_time = 0;
            break;
            
        case STATE_MOVE_PLATE_1:
            update_motors_from_pots_hbot();
            
            // Check if target reached
            if (check_target_reached(plate_1.target_x, plate_1.target_y)) {
                if (placement_start_time == 0) {
                    placement_start_time = current_time;
                }
                current_state = STATE_VERIFY_PLATE_1;
                update_lcd_for_state();
            }
            break;
            
        case STATE_VERIFY_PLATE_1:
            update_motors_from_pots_hbot();
            
            if (!check_target_reached(plate_1.target_x, plate_1.target_y)) {
                // Moved away, restart timer
                placement_start_time = 0;
                current_state = STATE_MOVE_PLATE_1;
                update_lcd_for_state();
            } else if (current_time - placement_start_time >= PLACEMENT_TIME) {
                // Successfully held position for 5 seconds
                magnet_release_hold();  // Reverse polarity, keep running
                motors_stop();
                buzzer_beep(500);
                plate_1.placed = true;
                sleep_ms(500);
                current_state = STATE_WAIT_PLATE_2;
                update_lcd_for_state();
                camera_data.marker_detected = false;
            }
            break;
            
        case STATE_WAIT_PLATE_2:
            // Two-step process: detect marker, then wait for button confirmation
            if (camera_data.marker_detected &&
                camera_data.detected_marker.grid_row == 0 &&
                camera_data.detected_marker.grid_col == 0) {
                
                if (!waiting_for_confirmation) {
                    // First time detecting marker - set flag and update LCD
                    waiting_for_confirmation = true;
                    update_lcd_for_state();
                    buzzer_beep(100);  // Beep to indicate detection
                } else if (button_check()) {
                    // Button pressed - proceed with pickup
                    waiting_for_confirmation = false;
                    current_state = STATE_PICK_PLATE_2;
                    update_lcd_for_state();
                    magnet_set(true);  // Turn on magnet after button confirmation
                    buzzer_beep(200);  // Different beep for confirmation
                }
            } else {
                // Marker not detected or moved - reset confirmation flag
                if (waiting_for_confirmation) {
                    waiting_for_confirmation = false;
                    update_lcd_for_state();
                }
            }
            break;
            
        case STATE_PICK_PLATE_2:
            sleep_ms(1000);
            current_state = STATE_MOVE_PLATE_2;
            update_lcd_for_state();
            placement_start_time = 0;
            break;
            
        case STATE_MOVE_PLATE_2:
            update_motors_from_pots_hbot();
            
            if (check_target_reached(plate_2.target_x, plate_2.target_y)) {
                if (placement_start_time == 0) {
                    placement_start_time = current_time;
                }
                current_state = STATE_VERIFY_PLATE_2;
                update_lcd_for_state();
            }
            break;
            
        case STATE_VERIFY_PLATE_2:
            update_motors_from_pots_hbot();
            
            if (!check_target_reached(plate_2.target_x, plate_2.target_y)) {
                placement_start_time = 0;
                current_state = STATE_MOVE_PLATE_2;
                update_lcd_for_state();
            } else if (current_time - placement_start_time >= PLACEMENT_TIME) {
                magnet_release_final();  // Reverse for 1 second, then off
                motors_stop();
                buzzer_beep(500);
                plate_2.placed = true;
                sleep_ms(500);
                current_state = STATE_COMPLETE;
                update_lcd_for_state();
                uv_led_set(true);
                buzzer_beep(1000);
            }
            break;
            
        case STATE_COMPLETE:
            // Task complete - motors stopped, UV on
            motors_stop();
            break;
    }
}

// ============================================================================
// MAIN FUNCTION
// ============================================================================

int main() {
    stdio_init_all();
    sleep_ms(2000); // Wait for USB serial
    
    printf("\n========================================\n");
    printf("FORGE REGISTRY STATION - ARUCO SYSTEM\n");
    printf("========================================\n");
    
    // Initialize all peripherals
    printf("Initializing peripherals...\n");
    lcd_init();
    lcd_clear();
    lcd_printf(0, 0, "HELLO WORLD");
    lcd_printf(0, 1, "LCD CHECK");
    sleep_ms(1500);
    lcd_clear();
    lcd_printf(0, 0, "FORGE REGISTRY");
    lcd_printf(0, 1, "INITIALIZING...");
    
    adc_init_all();
    motors_init();
    homing_init();
    magnet_init();
    buzzer_init();
    uv_led_init();
    button_init();
    
    buzzer_beep(100);
    
    printf("System ready (USB serial input)\n");
    
    // Startup delay: wait 10 seconds while displaying motor values
    printf("Startup delay: 10 seconds...\n");
    uint32_t start_time = to_ms_since_boot(get_absolute_time());
    uint32_t delay_duration = 10000; // 10 seconds
    
    while (to_ms_since_boot(get_absolute_time()) - start_time < delay_duration) {
        // Read pots and calculate motor commands (but don't move)
        adc_select_input(0);
        uint32_t sum_x = 0;
        for (int i = 0; i < 8; i++) {
            sum_x += adc_read();
            sleep_us(10);
        }
        debug_adc_x = sum_x / 8;
        
        adc_select_input(1);
        uint32_t sum_y = 0;
        for (int i = 0; i < 8; i++) {
            sum_y += adc_read();
            sleep_us(10);
        }
        debug_adc_y = sum_y / 8;
        
        int x_cmd = read_pot_with_deadzone(0);
        int y_cmd = read_pot_with_deadzone(1);
        
        // Calculate motor values
        int motor_a = x_cmd + y_cmd;
        int motor_b = x_cmd - y_cmd;
        if (motor_a > 255) motor_a = 255;
        if (motor_a < -255) motor_a = -255;
        if (motor_b > 255) motor_b = 255;
        if (motor_b < -255) motor_b = -255;
        
        // Display countdown and motor values
        uint32_t remaining = (delay_duration - (to_ms_since_boot(get_absolute_time()) - start_time)) / 1000;
        lcd_clear();
        lcd_set_cursor(0, 0);
        char buf0[17];
        snprintf(buf0, sizeof(buf0), "WAIT:%2ds A:%+4d", (int)remaining, motor_a);
        lcd_print(buf0);
        lcd_set_cursor(0, 1);
        char buf1[17];
        snprintf(buf1, sizeof(buf1), "X:%4d Y:%4d B:%+4d", debug_adc_x, debug_adc_y, motor_b);
        lcd_print(buf1);
        
        sleep_ms(200); // Update ~5Hz
    }
    
    // Startup movement test: move left for 1 second
    printf("Startup test: moving left...\n");
    lcd_clear();
    lcd_printf(0, 0, "STARTUP TEST");
    lcd_printf(0, 1, "Moving LEFT...");
    motor_set_l298(MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2, -100); // Left movement
    motor_set_l298(MOTOR_B_PWM, MOTOR_B_IN3, MOTOR_B_IN4, -100); // Both motors same direction
    sleep_ms(1000);
    motors_stop();
    sleep_ms(500);
    printf("Startup test complete\n");
    
    if (TEST_DISPLAY_ONLY) {
        // Test mode: skip state machine, just display pot readings
        printf("TEST MODE: Displaying pot inputs on LCD\n");
        lcd_clear();
        lcd_printf(0, 0, "TEST MODE");
        sleep_ms(1000);
        
        while (true) {
            update_motors_from_pots_hbot();
            
            // Display test values at 5Hz
            static uint32_t last_test_lcd = 0;
            uint32_t now = to_ms_since_boot(get_absolute_time());
            if (now - last_test_lcd > 200) {
                lcd_clear();
                lcd_set_cursor(0, 0);
                char buf0[17];
                snprintf(buf0, sizeof(buf0), "X:%4d Y:%4d", debug_adc_x, debug_adc_y);
                lcd_print(buf0);
                lcd_set_cursor(0, 1);
                char buf1[17];
                snprintf(buf1, sizeof(buf1), "A:%+4d B:%+4d", debug_motor_a, debug_motor_b);
                lcd_print(buf1);
                last_test_lcd = now;
            }
            
            sleep_ms(50); // ~20Hz update rate
        }
    } else {
        // Normal operation with full state machine
        current_state = STATE_INIT;
        
        while (true) {
            poll_serial();
            state_machine_update();
            update_lcd_periodic();  // Single place for all LCD updates
            sleep_ms(20); // 50Hz update rate for smoother control
        }
    }
    
    return 0;
}
