#include <Servo.h>
// Pin Definitions
#define TRIGGER_PIN 2
#define ECHO_PIN 3
#define RED_LED_PIN 4
#define BLUE_LED_PIN 5
#define SERVO_PIN 6
#define GND_PIN_1 7
#define GND_PIN_2 8
#define BUZZER_PIN 12
// System State
bool vehicleDetected = false;
unsigned long lastBeepTime = 0;
const float DETECTION_THRESHOLD = 20.0; // cm, change if needed
bool gateOpen = false;
unsigned long lastBuzzTime = 0;
const unsigned long buzzInterval = 300;
bool buzzerState = false;
bool alertActive = false; // New: Alert state flag
Servo barrierServo;
// ================== INITIALIZATION ==================
void initializeSerial() {
  Serial.begin(9600);
}
void initializeUltrasonic() {
  pinMode(TRIGGER_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
}
void initializeLEDs() {
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(BLUE_LED_PIN, OUTPUT);
}
void initializeBuzzer() {
  pinMode(BUZZER_PIN, OUTPUT);
}
void initializeHardcodedGrounds() {
  pinMode(GND_PIN_1, OUTPUT);
  pinMode(GND_PIN_2, OUTPUT);
  digitalWrite(GND_PIN_1, LOW);
  digitalWrite(GND_PIN_2, LOW);
}
void initializeServo() {
  barrierServo.attach(SERVO_PIN);
  setGatePosition(6); // Start with closed gate
}
// ================== CORE FUNCTIONS ==================
float measureDistance() {
  digitalWrite(TRIGGER_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH);
  return (duration * 0.0343) / 2.0;
}
void setGatePosition(int angle) {
  barrierServo.write(angle);
}

void beep(unsigned int duration = 100) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(duration);
  digitalWrite(BUZZER_PIN, LOW);
}
// ================== GATE CONTROL ==================
void openGate() {
  if(alertActive) return; // Prevent opening during alerts
  setGatePosition(90);
  gateOpen = true;
  digitalWrite(BLUE_LED_PIN, HIGH);
  digitalWrite(RED_LED_PIN, LOW);
  beep();  // Beep when gate opens
  Serial.println("[GATE] Opened");
}

void closeGate() {
  setGatePosition(6);
  gateOpen = false;
  digitalWrite(BLUE_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, HIGH);
  beep();  // Beep when gate closes
  Serial.println("[GATE] Closed");
}

// ================== ALERT SYSTEM ==================
void triggerAlert() {
  alertActive = true;
  digitalWrite(RED_LED_PIN, HIGH);
  digitalWrite(BUZZER_PIN, HIGH);
  Serial.println("[ALERT] Unpaid vehicle detected!");
}
void stopAlert() {
  alertActive = false;
  digitalWrite(RED_LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  Serial.println("[ALERT] Cleared");
}
// ================== COMMAND HANDLER ==================
void handleSerialCommands() {
  if (Serial.available()) {
    char cmd = Serial.read();
    switch(cmd) {
      case '1': // Open gate
        openGate();
        break;
      case '0': // Close gate
        closeGate();
        break;
      case '2': // Trigger alert
        triggerAlert();
        break;
      case '3': // Stop alert
        stopAlert();
        break;
      default:
        Serial.println("[ERROR] Unknown command");
    }
  }
}
// ================== BUZZER CONTROL ==================
void handleBuzzerOnDetection(float distance) {
  if (distance < DETECTION_THRESHOLD && !vehicleDetected && !alertActive) {
    // Vehicle just detected
    vehicleDetected = true;
    digitalWrite(BUZZER_PIN, HIGH);
    lastBeepTime = millis();
  }

  // Turn off buzzer after short beep
  if (vehicleDetected && (millis() - lastBeepTime > 100)) {
    digitalWrite(BUZZER_PIN, LOW);
  }

  // Reset detection if vehicle moves away
  if (distance >= DETECTION_THRESHOLD + 5) {
    vehicleDetected = false;
  }
}





// ================== MAIN LOOP ==================
void setup() {
  initializeSerial();
  initializeUltrasonic();
  initializeLEDs();
  initializeBuzzer();
  initializeHardcodedGrounds();
  initializeServo();
  // Initial state
  digitalWrite(RED_LED_PIN, HIGH); // Closed gate indicator
  Serial.println("[SYSTEM] Ready");
}
void loop() {
  // 1. Sensor monitoring
  float distance = measureDistance();
  Serial.print("[DISTANCE] ");
  Serial.println(distance);
  // 2. Command handling
  handleSerialCommands();
  // 3. Buzzer management
  handleBuzzerOnDetection(distance);
  delay(50); // Main loop delay
}