/*
 * Arduino Code for Grid Tracking System
 * Receives grid coordinates from Python via Serial
 * Displays position on LCD or Serial Monitor
 * 
 * Author: GitHub Copilot
 * Date: November 2025
 * 
 * Hardware Requirements:
 * - Arduino Uno/Mega/Nano or ESP32
 * - Optional: 16x2 I2C LCD Display
 * 
 * Wiring (if using LCD):
 * LCD SDA -> Arduino A4 (Uno) or GPIO21 (ESP32)
 * LCD SCL -> Arduino A5 (Uno) or GPIO22 (ESP32)
 * LCD VCC -> 5V
 * LCD GND -> GND
 */

// Uncomment if using I2C LCD
// #include <Wire.h>
// #include <LiquidCrystal_I2C.h>

// LCD Configuration (0x27 or 0x3F are common I2C addresses)
// LiquidCrystal_I2C lcd(0x27, 16, 2);

// Variables for receiving data
String inputString = "";
bool stringComplete = false;
int currentRow = -1;
int currentCol = -1;

// LED pins (optional - for visual feedback)
const int LED_PIN = 13;  // Built-in LED

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Initialize LED
  pinMode(LED_PIN, OUTPUT);
  
  // Initialize LCD (if using)
  /*
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Grid Tracker");
  lcd.setCursor(0, 1);
  lcd.print("Ready...");
  delay(2000);
  lcd.clear();
  */
  
  Serial.println("Arduino Grid Tracker Ready");
  Serial.println("Waiting for coordinates...");
  
  // Reserve memory for input string
  inputString.reserve(50);
}

void loop() {
  // Check if data is available
  if (stringComplete) {
    // Parse the received string "ROW,COL"
    int commaIndex = inputString.indexOf(',');
    
    if (commaIndex > 0) {
      String rowStr = inputString.substring(0, commaIndex);
      String colStr = inputString.substring(commaIndex + 1);
      
      currentRow = rowStr.toInt();
      currentCol = colStr.toInt();
      
      // Validate coordinates
      if (currentRow >= 0 && currentRow <= 4 && currentCol >= 0 && currentCol <= 4) {
        // Print to Serial Monitor
        Serial.print("Position: (");
        Serial.print(currentRow);
        Serial.print(", ");
        Serial.print(currentCol);
        Serial.println(")");
        
        // Update LCD (if using)
        /*
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Grid Position:");
        lcd.setCursor(0, 1);
        lcd.print("(");
        lcd.print(currentRow);
        lcd.print(", ");
        lcd.print(currentCol);
        lcd.print(")");
        */
        
        // Blink LED as feedback
        digitalWrite(LED_PIN, HIGH);
        delay(50);
        digitalWrite(LED_PIN, LOW);
        
        // Send acknowledgment back to Python
        Serial.println("ACK");
      }
      else {
        Serial.println("ERROR: Invalid coordinates");
      }
    }
    
    // Clear the string for next input
    inputString = "";
    stringComplete = false;
  }
  
  // Add any additional logic here
  // For example, control motors, servos, or other actuators based on position
}

// Serial event handler
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n') {
      stringComplete = true;
    }
    else {
      inputString += inChar;
    }
  }
}

/*
 * EXPANSION IDEAS:
 * 
 * 1. LED Matrix Display:
 *    Light up corresponding LED in a 5x5 LED matrix
 * 
 * 2. Servo Control:
 *    Move a servo to point at the detected position
 * 
 * 3. Robot Control:
 *    Control a robot to move to the target cell
 * 
 * 4. Game Logic:
 *    Implement tic-tac-toe or other games
 * 
 * 5. Data Logging:
 *    Store position history on SD card
 */
