/**
 * Forge Registry Station - Aruco Plate Positioning System
 * Manual Gantry Control with Real-time Camera Feedback
 * Pico W with WiFi, Motors, Potentiometers, LCD, and Electromagnet
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

// WiFi includes (must be after pico_stdlib)
#include "pico/cyw43_arch.h"
#include "lwip/pbuf.h"
#include "lwip/udp.h"

// ============================================================================
// PIN DEFINITIONS
// ============================================================================

// Potentiometers (Analog inputs for ADC)
#define POT_X_PIN       26  // ADC0 - X-axis control
#define POT_Y_PIN       27  // ADC1 - Y-axis control

// DC Motor Outputs (PWM for speed control)
#define MOTOR_X_PWM     2   // X-axis motor PWM
#define MOTOR_X_DIR     3   // X-axis motor direction
#define MOTOR_Y_PWM     4   // Y-axis motor PWM
#define MOTOR_Y_DIR     5   // Y-axis motor direction

// Limit Switches (for homing)
#define LIMIT_X_PIN     6   // X-axis limit switch
#define LIMIT_Y_PIN     7   // Y-axis limit switch

// Electromagnet
#define MAGNET_PIN      8   // Electromagnet control

// Push Button
#define BUTTON_PIN      9   // Stage start button

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
#define UDP_PORT            5000
#define ADC_MAX             4095    // 12-bit ADC
#define DEADZONE            200     // Potentiometer deadzone
#define PWM_MAX             65535   // 16-bit PWM
#define PLACEMENT_TIME      5000    // 5 seconds in milliseconds
#define BUTTON_DEBOUNCE     50      // Button debounce time (ms)

// WiFi Configuration
#define WIFI_SSID           "YOUR_WIFI_SSID"
#define WIFI_PASSWORD       "YOUR_WIFI_PASSWORD"

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
static struct udp_pcb *udp_pcb_global = NULL;
static bool button_pressed = false;
static uint32_t placement_start_time = 0;
static bool magnet_active = false;
static int qr_sequence[4] = {5, 4, 3, 2}; // Example: 5432 -> (5,4) and (3,2)

// ============================================================================
// LCD I2C FUNCTIONS (16x2 LCD)
// ============================================================================

void lcd_send_byte(uint8_t val, int mode) {
    uint8_t high = (val & 0xF0) | mode | 0x08; // Enable=1, backlight=1
    uint8_t low = ((val << 4) & 0xF0) | mode | 0x08;
    
    uint8_t data[4] = {high, high & ~0x04, low, low & ~0x04}; // Toggle enable
    i2c_write_blocking(i2c0, LCD_ADDR, data, 4, false);
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
    
    sleep_ms(100);
    lcd_send_cmd(0x03);
    lcd_send_cmd(0x03);
    lcd_send_cmd(0x03);
    lcd_send_cmd(0x02); // 4-bit mode
    lcd_send_cmd(0x28); // 2 lines, 5x8 font
    lcd_send_cmd(0x0C); // Display on, cursor off
    lcd_send_cmd(0x06); // Increment cursor
    lcd_send_cmd(0x01); // Clear display
    sleep_ms(2);
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
    gpio_set_function(MOTOR_X_PWM, GPIO_FUNC_PWM);
    gpio_set_function(MOTOR_Y_PWM, GPIO_FUNC_PWM);
    
    uint slice_x = pwm_gpio_to_slice_num(MOTOR_X_PWM);
    uint slice_y = pwm_gpio_to_slice_num(MOTOR_Y_PWM);
    
    pwm_set_wrap(slice_x, PWM_MAX);
    pwm_set_wrap(slice_y, PWM_MAX);
    pwm_set_enabled(slice_x, true);
    pwm_set_enabled(slice_y, true);
    
    // Initialize direction pins
    gpio_init(MOTOR_X_DIR);
    gpio_set_dir(MOTOR_X_DIR, GPIO_OUT);
    gpio_init(MOTOR_Y_DIR);
    gpio_set_dir(MOTOR_Y_DIR, GPIO_OUT);
}

void motor_set(uint gpio_pwm, uint gpio_dir, int speed) {
    // speed: -255 to +255 (negative = reverse)
    bool direction = speed >= 0;
    uint16_t pwm_value = (abs(speed) * PWM_MAX) / 255;
    
    gpio_put(gpio_dir, direction);
    pwm_set_gpio_level(gpio_pwm, pwm_value);
}

void motors_stop(void) {
    motor_set(MOTOR_X_PWM, MOTOR_X_DIR, 0);
    motor_set(MOTOR_Y_PWM, MOTOR_Y_DIR, 0);
}

// ============================================================================
// POTENTIOMETER CONTROL
// ============================================================================

void adc_init_all(void) {
    adc_init();
    adc_gpio_init(POT_X_PIN);
    adc_gpio_init(POT_Y_PIN);
}

int read_pot_with_deadzone(uint adc_channel) {
    adc_select_input(adc_channel);
    int raw = adc_read();
    
    int centered = raw - (ADC_MAX / 2);
    
    if (abs(centered) < DEADZONE) {
        return 0;
    }
    
    // Map to -255 to +255
    int speed = (centered * 255) / (ADC_MAX / 2);
    speed = (speed > 255) ? 255 : (speed < -255) ? -255 : speed;
    
    return speed;
}

void update_motors_from_pots(void) {
    int x_speed = read_pot_with_deadzone(0); // ADC0
    int y_speed = read_pot_with_deadzone(1); // ADC1
    
    motor_set(MOTOR_X_PWM, MOTOR_X_DIR, x_speed);
    motor_set(MOTOR_Y_PWM, MOTOR_Y_DIR, y_speed);
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
        motor_set(MOTOR_X_PWM, MOTOR_X_DIR, -100); // Move backwards
        sleep_ms(10);
    }
    motors_stop();
    sleep_ms(500);
    
    // Home Y-axis
    while (!gpio_get(LIMIT_Y_PIN)) {
        motor_set(MOTOR_Y_PWM, MOTOR_Y_DIR, -100);
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
// UDP RECEIVE CALLBACK
// ============================================================================

void udp_recv_callback(void *arg, struct udp_pcb *pcb, struct pbuf *p,
                       const ip_addr_t *addr, u16_t port) {
    if (p != NULL) {
        char *data = (char *)p->payload;
        
        // Simple JSON parsing (look for "id", "grid_row", "grid_col")
        // Example: {"markers":[{"id":1,"grid_row":0,"grid_col":0,...}]}
        
        char *id_str = strstr(data, "\"id\":");
        char *row_str = strstr(data, "\"grid_row\":");
        char *col_str = strstr(data, "\"grid_col\":");
        
        if (id_str && row_str && col_str) {
            int id = atoi(id_str + 5);
            int row = atoi(row_str + 11);
            int col = atoi(col_str + 11);
            
            camera_data.detected_marker.id = id;
            camera_data.detected_marker.grid_row = row;
            camera_data.detected_marker.grid_col = col;
            camera_data.detected_marker.valid = true;
            camera_data.marker_detected = true;
            camera_data.current_x = col;
            camera_data.current_y = row;
            camera_data.last_update_time = to_ms_since_boot(get_absolute_time());
            
            printf("Received marker: ID=%d at (%d,%d)\n", id, row, col);
        }
        
        // Send acknowledgment
        char ack[] = "{\"state\":\"OK\"}";
        struct pbuf *p_ack = pbuf_alloc(PBUF_TRANSPORT, strlen(ack), PBUF_RAM);
        if (p_ack != NULL) {
            memcpy(p_ack->payload, ack, strlen(ack));
            udp_sendto(pcb, p_ack, addr, port);
            pbuf_free(p_ack);
        }
        
        pbuf_free(p);
    }
}

// ============================================================================
// WIFI INITIALIZATION
// ============================================================================

bool wifi_init_sta(void) {
    if (cyw43_arch_init()) {
        printf("WiFi init failed\n");
        return false;
    }
    
    cyw43_arch_enable_sta_mode();
    
    printf("Connecting to WiFi: %s\n", WIFI_SSID);
    if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD, 
                                           CYW43_AUTH_WPA2_AES_PSK, 30000)) {
        printf("WiFi connection failed\n");
        return false;
    }
    
    printf("WiFi connected!\n");
    printf("IP: %s\n", ip4addr_ntoa(netif_ip4_addr(netif_list)));
    
    // Setup UDP server
    udp_pcb_global = udp_new();
    if (udp_pcb_global != NULL) {
        err_t err = udp_bind(udp_pcb_global, IP_ADDR_ANY, UDP_PORT);
        if (err == ERR_OK) {
            udp_recv(udp_pcb_global, udp_recv_callback, NULL);
            printf("UDP server listening on port %d\n", UDP_PORT);
            return true;
        }
    }
    
    printf("UDP setup failed\n");
    return false;
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
            lcd_printf(0, 1, "at (1,1) BTN=GO");
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
            lcd_printf(0, 1, "at (1,1) BTN=GO");
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
                current_state = STATE_WAIT_PLATE_1;
                update_lcd_for_state();
            }
            break;
            
        case STATE_WAIT_PLATE_1:
            if (button_check()) {
                if (camera_data.marker_detected && 
                    (camera_data.detected_marker.id == 1 || 
                     camera_data.detected_marker.id == 2)) {
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
                    current_state = STATE_PICK_PLATE_1;
                    update_lcd_for_state();
                    magnet_set(true);
                    buzzer_beep(100);
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
            update_motors_from_pots();
            
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
            update_motors_from_pots();
            
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
            if (button_check()) {
                if (camera_data.marker_detected) {
                    current_state = STATE_PICK_PLATE_2;
                    update_lcd_for_state();
                    magnet_set(true);
                    buzzer_beep(100);
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
            update_motors_from_pots();
            
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
            update_motors_from_pots();
            
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
            // Stay in complete state
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
    
    // Initialize WiFi
    printf("Connecting to WiFi...\n");
    lcd_clear();
    lcd_printf(0, 0, "CONNECTING WIFI");
    
    if (!wifi_init_sta()) {
        printf("WiFi initialization failed!\n");
        lcd_clear();
        lcd_printf(0, 0, "WIFI FAILED!");
        while (1) {
            tight_loop_contents();
        }
    }
    
    lcd_clear();
    lcd_printf(0, 0, "WIFI CONNECTED");
    sleep_ms(2000);
    
    printf("System ready!\n");
    current_state = STATE_INIT;
    
    // Main loop
    while (true) {
        cyw43_arch_poll(); // Handle WiFi events
        state_machine_update();
        sleep_ms(10); // Small delay to prevent tight loop
    }
    
    return 0;
}
