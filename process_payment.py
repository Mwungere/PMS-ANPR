import serial
import time
import serial.tools.list_ports
import platform
from datetime import datetime
from db_operations import get_last_unpaid_entry, update_payment_status, get_parking_duration
import math

# Amount charged per hour (RWF 500)
RATE_PER_HOUR = 500

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
            if "COM10" in port.device:
                return port.device
    return None

def parse_arduino_data(line):
    """Parse the data received from Arduino"""
    try:
        # Skip header lines
        if "PAYMENT MODE RFID" in line:
            return None, None

        # Split the data by comma
        parts = line.strip().split(',')
        print(f"[ARDUINO] Parsed parts: {parts}")
        
        if len(parts) != 2:
            return None, None
            
        plate = parts[0].strip()
        
        # Clean the balance string by removing non-digit characters
        balance_str = ''.join(c for c in parts[1] if c.isdigit())
        print(f"[ARDUINO] Cleaned balance: {balance_str}")
        
        if balance_str:
            balance = int(balance_str)
            return plate, balance
        else:
            return None, None
    except ValueError as e:
        print(f"[ERROR] Value error in parsing: {e}")
        return None, None
    except Exception as e:
        print(f"[ERROR] Error parsing Arduino data: {e}")
        return None, None

def calculate_parking_fee(minutes_spent):
    """Calculate parking fee based on time spent"""
    # Calculate rate per minute (500 RWF / 60 minutes = 8.33... RWF per minute)
    rate_per_minute = RATE_PER_HOUR / 60.0
    
    # Calculate exact amount based on minutes
    exact_amount = minutes_spent * rate_per_minute
    
    # Round to nearest whole number
    return round(exact_amount)

def process_payment(plate, balance, ser):
    """Process payment for a plate number"""
    entry = get_last_unpaid_entry(plate)
    if entry:
        minutes_spent = get_parking_duration(entry['entry_timestamp'])
        amount_due = calculate_parking_fee(minutes_spent)
        
        # Calculate hours and minutes for display
        hours = minutes_spent // 60
        minutes = minutes_spent % 60
        
        # Calculate and display rate details
        rate_per_minute = RATE_PER_HOUR / 60.0
        
        # Print payment details
        print(f"[PAYMENT] Time spent: {hours} hours and {minutes} minutes ({minutes_spent} total minutes)")
        print(f"[PAYMENT] Rate: RWF {RATE_PER_HOUR} per hour (RWF {rate_per_minute:.2f} per minute)")
        print(f"[PAYMENT] Amount due: RWF {amount_due}")
        print(f"[PAYMENT] Balance available: RWF {balance}")
        
        if balance >= amount_due:
            success = update_payment_status(
                plate,
                entry['entry_timestamp'],
                amount_due
            )
            if success:
                # Calculate new balance
                new_balance = balance - amount_due
                print(f"[PAYMENT] Processed payment of RWF {amount_due} for {plate}")
                print(f"[PAYMENT] New balance: RWF {new_balance}")
                
                # Send new balance to Arduino
                if ser:
                    ser.write(f"{new_balance}\n".encode())
                    print(f"[ARDUINO] Sent new balance: {new_balance}")
                return True
            else:
                print(f"[ERROR] Failed to process payment for {plate}")
                if ser:
                    ser.write("I\n".encode())  # Send 'I' for invalid/error
        else:
            print(f"[ERROR] Insufficient balance. Required: RWF {amount_due}, Available: RWF {balance}")
            if ser:
                ser.write("I\n".encode())  # Send 'I' for insufficient funds
    else:
        print(f"[ERROR] No unpaid entry found for {plate}")
        if ser:
            ser.write("I\n".encode())  # Send 'I' for invalid/error
    return False

# Initialize Arduino connection
arduino_port = detect_arduino_port()
if arduino_port:
    print(f"[CONNECTED] Arduino on {arduino_port}")
    arduino = serial.Serial(arduino_port, 9600, timeout=1)
    time.sleep(2)
else:
    print("[ERROR] Arduino not detected.")
    arduino = None

def main():
    try:
        while True:
            if arduino.in_waiting:
                line = arduino.readline().decode().strip()
                print(f"[SERIAL] Received: {line}")
                plate, balance = parse_arduino_data(line)
                if plate and balance is not None:
                    process_payment(plate, balance, arduino)

    except KeyboardInterrupt:
        print("[EXIT] Program terminated")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if 'arduino' in locals():
            arduino.close()

if __name__ == "__main__":
    main()