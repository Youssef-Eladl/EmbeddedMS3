
// ----------------------------------------------------------------------------
// CAMERA FEEDBACK → LCD
// ----------------------------------------------------------------------------
// Shows latest parsed camera values on the 16x2 LCD.
static void lcd_show_camera_feedback(void) {
    // Line 0: Marker ID and grid (display 1-based grid for readability)
    char line0[17];
    int id = camera_data.detected_marker.id;
    int r = camera_data.detected_marker.grid_row;
    int c = camera_data.detected_marker.grid_col;
    if (r < 0) r = 0; if (c < 0) c = 0; // basic safety
    lcd_set_cursor(0, 0);
    snprintf(line0, sizeof(line0), "ID:%3d R:%d C:%d", id, r + 1, c + 1);
    lcd_print(line0);

    // Line 1: X/Y (1-based) and age since last update
    uint32_t now = to_ms_since_boot(get_absolute_time());
    uint32_t age_ms = now - camera_data.last_update_time;
    char line1[17];
    lcd_set_cursor(0, 1);
    snprintf(line1, sizeof(line1), "X:%d Y:%d %4dms", camera_data.current_x + 1, camera_data.current_y + 1, (int)age_ms);
    lcd_print(line1);
}

// Replace omitted body: parse CSV from Python and update LCD
void handle_serial_line(const char *line);
void handle_serial_line(const char *line) {
    // Expected format from Python: "id,row,col\n" with 0-based indices
    int id = 0, row = 0, col = 0;
    if (sscanf(line, "%d,%d,%d", &id, &row, &col) == 3) {
        camera_data.detected_marker.id = id;
        camera_data.detected_marker.grid_row = row;
        camera_data.detected_marker.grid_col = col;
        camera_data.detected_marker.valid = true;
        camera_data.marker_detected = true;

        // Update current position tracking as row/col
        camera_data.current_x = col;
        camera_data.current_y = row;
        camera_data.last_update_time = to_ms_since_boot(get_absolute_time());

        // Show on LCD, throttled to every 5 seconds to avoid flicker
        uint32_t now = camera_data.last_update_time;
        if (now - last_lcd_update_ms >= LCD_UPDATE_INTERVAL_MS) {
            lcd_show_camera_feedback();
            last_lcd_update_ms = now;
        }
    }
}
/**
 * Forge Registry Station - Aruco Plate Positioning System
 * Manual Gantry Control with Real-time Camera Feedback
 * Pico with USB Serial Camera Input, Dual-Pot H-Bot Motion, LCD, and Electromagnet
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
#define MOTOR_A_IN1     17  // Motor A direction input 1
#define MOTOR_A_IN2     16  // Motor A direction input 2
#define MOTOR_B_PWM     13  // Motor B PWM (ENB)
#define MOTOR_B_IN3     19  // Motor B direction input 3
#define MOTOR_B_IN4     18  // Motor B direction input 4

// Limit Switches (for homing)
#define LIMIT_X_PIN     6   // X-axis limit switch
#define LIMIT_Y_PIN     7   // Y-axis limit switch

// Electromagnet
#define MAGNET_PIN      8   // Electromagnet control

// Push Button
#define BUTTON_PIN      22   // Stage start button

// Buzzer
#define BUZZER_PIN      10  // Confirmation buzzer

// UV LED
#define UV_LED_PIN      11  // Reward UV LED

// LCD I2C (Uses I2C0)
#define I2C_SDA_PIN     0   // I2C0 SDA
#define I2C_SCL_PIN     1   // I2C0 SCL
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
static int qr_sequence[4] = {5, 4, 3, 2}; // Example: 5432 -> (5,4) and (3,2)
static int16_t debug_motor_a = 0;
static int16_t debug_motor_b = 0;
static uint32_t last_debug_lcd_ms = 0;
static uint16_t debug_adc_x = 0;
static uint16_t debug_adc_y = 0;
static int16_t debug_x_cmd = 0;
static int16_t debug_y_cmd = 0;
static uint32_t motors_unlock_time = 0;
static bool motors_unlocked = false;
// LCD update throttle: wait at least 5 seconds between camera refreshes
static const uint32_t LCD_UPDATE_INTERVAL_MS = 5000;
static uint32_t last_lcd_update_ms = 0;

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
    // Average 8 readings to reduce noise
    uint32_t sum = 0;
    for (int i = 0; i < 8; i++) {
        adc_select_input(adc_channel);
        sum += adc_read();
        sleep_us(10);
    }
    int raw = sum / 8;
    
    int mid = ADC_MAX / 2;          // ~2047 corresponds to 1.65V (3.3V/2)
    int centered = raw - mid;        // negative below 1.65V, positive above

    // Small deadzone around center (~0.02V default)
    if (abs(centered) < DEADZONE) {
        return 0;
    }

    // Normalize to -1..+1 using 1.65V span, then scale to -255..255
    float norm = (float)centered / (float)mid;
    float scaled = norm * 255.0f;
    if (scaled > 255.0f) scaled = 255.0f;
    if (scaled < -255.0f) scaled = -255.0f;
    return (int)scaled;
}

static void update_motors_from_pots_hbot(void) {
    // Read raw ADC values for debugging
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
    
    int x_cmd = read_pot_with_deadzone(0); // ADC0 -> X axis
    int y_cmd = read_pot_with_deadzone(1); // ADC1 -> Y axis
    debug_x_cmd = x_cmd;
    debug_y_cmd = y_cmd;
    hbot_drive(x_cmd, y_cmd);

    // Display values for testing
    uint32_t now = to_ms_since_boot(get_absolute_time());
    if (now - last_debug_lcd_ms > 200) { // update ~5 Hz to reduce flicker
        const char* dir = get_direction_str(debug_motor_a, debug_motor_b);
        
        if (TEST_DISPLAY_ONLY) {
            // Line 0: Raw ADC values (0-4095)
            lcd_set_cursor(0, 0);
            char buf0[17];
            snprintf(buf0, sizeof(buf0), "X:%4d Y:%4d", debug_adc_x, debug_adc_y);
            lcd_print(buf0);
            // Line 1: Computed commands and motor outputs
            lcd_set_cursor(0, 1);
            char buf1[17];
            snprintf(buf1, sizeof(buf1), "A:%+4d B:%+4d", debug_motor_a, debug_motor_b);
            lcd_print(buf1);
        } else {
            // Normal mode: motor commands + direction
            lcd_set_cursor(0, 0);
            char buf0[17];
            snprintf(buf0, sizeof(buf0), "A:%+4d B:%+4d", debug_motor_a, debug_motor_b);
            lcd_print(buf0);
            
            lcd_set_cursor(0, 1);
            char buf1[17];
            if (!motors_unlocked) {
                uint32_t remaining = (motors_unlock_time - now + 999) / 1000; // Round up
                snprintf(buf1, sizeof(buf1), "%s WAIT:%ds", dir, (int)remaining);
            } else {
                snprintf(buf1, sizeof(buf1), "DIR: %s", dir);
            }
            lcd_print(buf1);
        }
        last_debug_lcd_ms = now;
    }
}

static void hbot_drive(int x_cmd, int y_cmd) {
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
    
    // Check if motors are unlocked (10 second wait after homing)
    if (!motors_unlocked) {
        motors_stop();
        return;
    }
    
    // Motors unlocked - normal operation
    motor_set_l298(MOTOR_A_PWM, MOTOR_A_IN1, MOTOR_A_IN2, motor_a);
    motor_set_l298(MOTOR_B_PWM, MOTOR_B_IN3, MOTOR_B_IN4, motor_b);
}

// ============================================================================
// HOMING FUNCTIONS
// ============================================================================

void homing_init(void) {
    gpio_init(LIMIT_X_PIN);
    gpio_set_dir(LIMIT_X_PIN, GPIO_IN);
    gpio_pull_up(LIMIT_X_PIN);
    
    gpio_init(LIMIT_Y_PIN);
    gpio_set_dir(LIMIT_Y_PIN, GPIO_IN);
    gpio_pull_up(LIMIT_Y_PIN);
}

bool homing_sequence(void) {
    lcd_clear();
    lcd_printf(0, 0, "HOMING...");
    
    // Home X-axis
    while (!gpio_get(LIMIT_X_PIN)) {
        hbot_drive(-100, 0); // Negative X: both motors CCW
        sleep_ms(10);
    }
    motors_stop();
    sleep_ms(500);
    
    // Home Y-axis
    while (!gpio_get(LIMIT_Y_PIN)) {
        hbot_drive(0, -100); // Negative Y: motors opposite
        sleep_ms(10);
    }
    motors_stop();
    
    camera_data.current_x = 0;
    camera_data.current_y = 0;
    
    lcd_clear();
    lcd_printf(0, 0, "HOMING COMPLETE");
    sleep_ms(1000);
    
    return true;
}

// ============================================================================
// ELECTROMAGNET & BUZZER
// ============================================================================

void magnet_init(void) {
    gpio_init(MAGNET_PIN);
    gpio_set_dir(MAGNET_PIN, GPIO_OUT);
    gpio_put(MAGNET_PIN, 0);
}

void magnet_set(bool active) {
    gpio_put(MAGNET_PIN, active);
    magnet_active = active;
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
    // QR sequence: [5, 4, 3, 2] means:
    // Plate 1 target: (5, 4) -> grid indices (4, 3) in 0-based
    // Plate 2 target: (3, 2) -> grid indices (2, 1) in 0-based
    
    plate_1.target_x = qr_sequence[0] - 1; // Convert to 0-based
    plate_1.target_y = qr_sequence[1] - 1;
    plate_1.placed = false;
    
    plate_2.target_x = qr_sequence[2] - 1;
    plate_2.target_y = qr_sequence[3] - 1;
    plate_2.placed = false;
    
    printf("Target 1: (%d,%d)\n", plate_1.target_x + 1, plate_1.target_y + 1);
    printf("Target 2: (%d,%d)\n", plate_2.target_x + 1, plate_2.target_y + 1);
}

// ============================================================================
// STATE MACHINE LOGIC
// ============================================================================

void update_lcd_for_state(void) {
    lcd_clear();
    
    switch (current_state) {
        case STATE_WAIT_PLATE_1:
            lcd_printf(0, 0, "PLACE ARUCO");
            lcd_printf(0, 1, "at (1,1)");
            break;
            
        case STATE_PICK_PLATE_1:
            lcd_printf(0, 0, "ID %d DETECTED", camera_data.detected_marker.id);
            lcd_printf(0, 1, "T:(%d,%d) PICK", 
                      plate_1.target_x + 1, plate_1.target_y + 1);
            break;
            
        case STATE_MOVE_PLATE_1:
            lcd_printf(0, 0, "T:(%d,%d) C:(%d,%d)", 
                      plate_1.target_x + 1, plate_1.target_y + 1,
                      camera_data.current_x + 1, camera_data.current_y + 1);
            lcd_printf(0, 1, "Use Pots to Move");
            break;
            
        case STATE_VERIFY_PLATE_1:
            lcd_printf(0, 0, "VERIFYING...");
            lcd_printf(0, 1, "Hold position");
            break;
            
        case STATE_WAIT_PLATE_2:
            lcd_printf(0, 0, "ADD ARUCO #2");
            lcd_printf(0, 1, "at (1,1)");
            break;
            
        case STATE_PICK_PLATE_2:
            lcd_printf(0, 0, "ID %d DETECTED", camera_data.detected_marker.id);
            lcd_printf(0, 1, "T:(%d,%d) PICK", 
                      plate_2.target_x + 1, plate_2.target_y + 1);
            break;
            
        case STATE_MOVE_PLATE_2:
            lcd_printf(0, 0, "T:(%d,%d) C:(%d,%d)", 
                      plate_2.target_x + 1, plate_2.target_y + 1,
                      camera_data.current_x + 1, camera_data.current_y + 1);
            lcd_printf(0, 1, "Use Pots to Move");
            break;
            
        case STATE_VERIFY_PLATE_2:
            lcd_printf(0, 0, "VERIFYING...");
            lcd_printf(0, 1, "Hold position");
            break;
            
        case STATE_COMPLETE:
            lcd_printf(0, 0, "** SUCCESS! **");
            lcd_printf(0, 1, "UV LIGHT ON");
            break;
            
        default:
            break;
    }
}

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
            current_state = STATE_HOMING;
            break;
            
        case STATE_HOMING:
            if (homing_sequence()) {
                // Skip plate placement for now - just loop pot control
                // Set 10-second motor lock
                motors_unlocked = false;
                motors_unlock_time = to_ms_since_boot(get_absolute_time()) + 10000;
                lcd_clear();
                lcd_printf(0, 0, "HOMING DONE");
                lcd_printf(0, 1, "10s WAIT...");
                sleep_ms(1500);
                current_state = STATE_COMPLETE;
            }
            break;
            
        case STATE_WAIT_PLATE_1:
            // Disabled for now
            break;
            
        case STATE_PICK_PLATE_1:
            sleep_ms(1000); // Wait for magnet to grab
            current_state = STATE_MOVE_PLATE_1;
            update_lcd_for_state();
            placement_start_time = 0;
            break;
            
        case STATE_MOVE_PLATE_1:
            update_motors_from_pots_hbot();
            
            // Update LCD with current position
            if (current_time % 200 < 10) { // Update every ~200ms
                update_lcd_for_state();
            }
            
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
                magnet_set(false);
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
            if (camera_data.marker_detected) {
                current_state = STATE_PICK_PLATE_2;
                update_lcd_for_state();
                magnet_set(true);
                buzzer_beep(100);
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
            
            if (current_time % 200 < 10) {
                update_lcd_for_state();
            }
            
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
                magnet_set(false);
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
            // Check if 10-second wait is over
            if (!motors_unlocked) {
                if (to_ms_since_boot(get_absolute_time()) >= motors_unlock_time) {
                    motors_unlocked = true;
                    buzzer_beep(200); // Signal motors are now active
                }
            }
            // Manual pot control - update motors continuously (respects unlock)
            update_motors_from_pots_hbot();
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
    
    if (TEST_DISPLAY_ONLY) {
        // Test mode: skip state machine, just display pot readings
        printf("TEST MODE: Displaying pot inputs on LCD\n");
        lcd_clear();
        lcd_printf(0, 0, "TEST MODE");
        sleep_ms(1000);
        
        while (true) {
            update_motors_from_pots_hbot();
            sleep_ms(50); // ~20Hz update rate
        }
    } else {
        // Normal operation with full state machine
        current_state = STATE_INIT;
        
        while (true) {
            poll_serial();
            state_machine_update();
            sleep_ms(10); // Small delay to prevent tight loop
        }
    }
    
    return 0;
}
