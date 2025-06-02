import cv2
from ultralytics import YOLO
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import os
import time
import serial
import serial.tools.list_ports
from collections import Counter
import random
from db_operations import (
    is_payment_complete,
    update_exit_timestamp,
    add_alert,
    get_last_unpaid_entry
)
import platform

# Load YOLOv8 model (same model as entry)
model = YOLO(r'best.pt')

# Initialize Arduino connection
def detect_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    system = platform.system()
    for port in ports:
        if system == "Linux":
            if "ttyUSB" in port.device or "ttyACM" in port.device:
                return port.device
        elif system == "Darwin":
            if "usbmodem" in port.device or "usbserial" in port.device:
                return port.device
        elif system == "Windows":
            if "COM11" in port.device:  # Assuming COM11 is your Arduino port
                return port.device
    return None

# Global arduino object
arduino_port = detect_arduino_port()
arduino = None
if arduino_port:
    try:
        arduino = serial.Serial(arduino_port, 9600, timeout=1)
        time.sleep(2)  # Wait for Arduino to initialize
        print(f"[CONNECTED] Arduino on {arduino_port}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Arduino: {e}")
else:
    print("[ERROR] Arduino not detected.")

def is_valid_plate(plate):
    """Validate plate number format"""
    if not plate or len(plate) != 7:
        return False
    
    # Check format: 3 letters + 3 digits + 1 letter
    prefix = plate[:3]
    digits = plate[3:6]
    suffix = plate[6]
    
    return (prefix.isalpha() and prefix.isupper() and
            digits.isdigit() and 
            suffix.isalpha() and suffix.isupper())

def parse_arduino_data(line):
    """Parse the data received from Arduino"""
    try:
        # Skip header lines
        if "EXIT MODE RFID" in line:
            return None

        # Clean and parse the plate number
        plate = line.strip()
        if plate and is_valid_plate(plate):
            return plate
        return None
    except Exception as e:
        print(f"[ERROR] Error parsing Arduino data: {e}")
        return None

def process_exit(plate):
    """Process vehicle exit"""
    if not is_valid_plate(plate):
        print(f"[ERROR] Invalid plate number format: {plate}")
        return False

    # Check payment status and process exit
    if is_payment_complete(plate):
        # Update exit timestamp
        if update_exit_timestamp(plate):
            print(f"[EXIT] Vehicle {plate} exited successfully")
            return True
    else:
        # Log unauthorized exit attempt
        add_alert(
            "UNAUTHORIZED_EXIT",
            plate,
            f"Vehicle {plate} attempted to exit without payment"
        )
        print(f"[ALERT] Unauthorized exit attempt by {plate}")
        # Send multiple buzzer signals for better alert
        if arduino:
            for _ in range(3):  # Buzz 3 times
                arduino.write(b'2')  # Trigger warning buzzer
                time.sleep(0.1)
                arduino.write(b'0')  # Stop buzzer
                time.sleep(0.1)
            print("[ALERT] Buzzer triggered multiple times")
        return False

# ===== Ultrasonic Sensor (mock for now) =====
def mock_ultrasonic_distance():
    return random.choice([random.randint(10, 40)])

def main():
    # Initialize camera
    cap = cv2.VideoCapture(0)
    plate_buffer = []
    unauthorized_cooldown = 0  # Cooldown timer for unauthorized attempts

    print("[EXIT SYSTEM] Ready. Press 'q' to quit.")

    try:
        while True:
            # Check if we're in cooldown period after unauthorized attempt
            if unauthorized_cooldown > 0:
                unauthorized_cooldown -= 1
                time.sleep(1)  # Wait 1 second
                if unauthorized_cooldown == 0:
                    print("[SYSTEM] Scanner reactivated after cooldown")
                continue

            # Check for Arduino data
            if arduino and arduino.in_waiting:
                line = arduino.readline().decode().strip()
                print(f"[SERIAL] Received: {line}")
                plate = parse_arduino_data(line)
                if plate:
                    if not process_exit(plate):
                        # Set cooldown period (30 seconds) after unauthorized attempt
                        unauthorized_cooldown = 30
                        if arduino:
                            arduino.write(b'2')  # Trigger warning buzzer
                            print("[ALERT] Buzzer triggered (sent '2')")
                        continue

            # Process camera feed
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to grab frame")
                break

            distance = mock_ultrasonic_distance()

            if distance <= 50:
                results = model(frame)

                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        plate_img = frame[y1:y2, x1:x2]

                        # Preprocessing
                        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                        blur = cv2.GaussianBlur(gray, (5, 5), 0)
                        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

                        # OCR
                        plate_text = pytesseract.image_to_string(
                            thresh, config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                        ).strip().replace(" ", "")

                        if "RA" in plate_text:
                            start_idx = plate_text.find("RA")
                            plate_candidate = plate_text[start_idx:]
                            if len(plate_candidate) >= 7:
                                plate_candidate = plate_candidate[:7]
                                if is_valid_plate(plate_candidate):
                                    print(f"[VALID] Plate Detected: {plate_candidate}")
                                    plate_buffer.append(plate_candidate)

                                    if len(plate_buffer) >= 3:
                                        most_common = Counter(plate_buffer).most_common(1)[0][0]
                                        plate_buffer.clear()

                                        if process_exit(most_common):
                                            if arduino:
                                                arduino.write(b'1')  # Open gate
                                                print("[GATE] Opening gate (sent '1')")
                                                time.sleep(15)
                                                arduino.write(b'0')  # Close gate
                                                print("[GATE] Closing gate (sent '0')")
                                        else:
                                            # Set cooldown period after unauthorized attempt
                                            unauthorized_cooldown = 30
                                            if arduino:
                                                arduino.write(b'2')  # Trigger warning buzzer
                                                print("[ALERT] Buzzer triggered (sent '2')")
                                            continue

                        cv2.imshow("Plate", plate_img)
                        cv2.imshow("Processed", thresh)

                annotated_frame = results[0].plot() if distance <= 50 else frame
                cv2.imshow("Exit Webcam Feed", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("[EXIT] Program terminated")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        cap.release()
        if arduino:
            arduino.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()