import cv2
from ultralytics import YOLO
import os
import time
import serial
import serial.tools.list_ports
from collections import Counter
import pytesseract
from db_operations import add_parking_entry, is_vehicle_inside, add_alert

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
model = YOLO(r'best.pt')
save_dir = 'plates'
os.makedirs(save_dir, exist_ok=True)

def detect_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "Arduino" in port.description or "COM11" in port.description or "USB-SERIAL" in port.description:
            return port.device
    return None

# Initialize Arduino connection
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

def mock_ultrasonic_distance():
    """Mock function for ultrasonic sensor"""
    return 30  # Simulated distance in cm

cap = cv2.VideoCapture(0)
plate_buffer = []
entry_cooldown = 300  # 5 minutes cooldown
last_saved_plate = None
last_entry_time = 0

print("[SYSTEM] Ready. Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    distance = mock_ultrasonic_distance()
    print(f"[SENSOR] Distance: {distance} cm")

    if distance <= 50:
        results = model(frame)

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                plate_img = frame[y1:y2, x1:x2]

                gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

                plate_text = pytesseract.image_to_string(
                    thresh,
                    config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                ).strip().replace(" ", "")

                if "RA" in plate_text:
                    start_idx = plate_text.find("RA")
                    plate_candidate = plate_text[start_idx:]
                    if len(plate_candidate) >= 7:
                        plate_candidate = plate_candidate[:7]
                        prefix, digits, suffix = plate_candidate[:3], plate_candidate[3:6], plate_candidate[6]
                        if (prefix.isalpha() and prefix.isupper() and
                            digits.isdigit() and suffix.isalpha() and suffix.isupper()):
                            print(f"[VALID] Plate Detected: {plate_candidate}")
                            plate_buffer.append(plate_candidate)

                            timestamp_str = time.strftime('%Y%m%d_%H%M%S')
                            image_filename = f"{plate_candidate}_{timestamp_str}.jpg"
                            save_path = os.path.join(save_dir, image_filename)
                            cv2.imwrite(save_path, plate_img)
                            print(f"[IMAGE SAVED] {save_path}")

                            if len(plate_buffer) >= 3:
                                most_common = Counter(plate_buffer).most_common(1)[0][0]
                                current_time = time.time()

                                # Check if vehicle is already inside
                                if is_vehicle_inside(most_common):
                                    print(f"[DENIED] Vehicle {most_common} is already in the parking lot")
                                    # Log unauthorized entry attempt
                                    add_alert(
                                        "DUPLICATE_ENTRY",
                                        most_common,
                                        f"Vehicle {most_common} attempted to enter while already inside"
                                    )
                                    # Trigger warning buzzer
                                    if arduino:
                                        for _ in range(3):  # Buzz 3 times
                                            arduino.write(b'2')  # Trigger warning buzzer
                                            time.sleep(0.5)
                                            arduino.write(b'0')  # Stop buzzer
                                            time.sleep(0.5)
                                        print("[ALERT] Buzzer triggered for duplicate entry")
                                    plate_buffer.clear()
                                    continue

                                if (most_common != last_saved_plate or
                                    (current_time - last_entry_time) > entry_cooldown):
                                    
                                    # Add entry to database
                                    entry_id = add_parking_entry(most_common)
                                    if entry_id:
                                        print(f"[SAVED] {most_common} logged to database.")
                                        if arduino:
                                            arduino.write(b'1')
                                            print("[GATE] Opening gate (sent '1')")
                                            time.sleep(15)
                                            arduino.write(b'0')
                                            print("[GATE] Closing gate (sent '0')")
                                        last_saved_plate = most_common
                                        last_entry_time = current_time
                                    else:
                                        print(f"[ERROR] Failed to log {most_common} to database.")
                                else:
                                    print("[SKIPPED] Duplicate within 5 min window.")
                                plate_buffer.clear()

                cv2.imshow("Plate", plate_img)
                cv2.imshow("Processed", thresh)
                time.sleep(0.5)

    annotated_frame = results[0].plot() if distance <= 50 else frame
    cv2.imshow('Webcam Feed', annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if arduino:
    arduino.close()
cv2.destroyAllWindows()