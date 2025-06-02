from db_operations import update_payment_status, get_last_unpaid_entry

def mark_payment_success(plate_number):
    """Mark a plate number's payment as successful"""
    entry = get_last_unpaid_entry(plate_number)
    if entry:
        success = update_payment_status(
            plate_number,
            entry['entry_timestamp'],
            None  # Amount paid not available
        )
        if success:
            print(f"[UPDATED] Payment status set to paid for {plate_number}")
        else:
            print(f"[ERROR] Failed to update payment status for {plate_number}")
    else:
        print(f"[INFO] No unpaid record found for {plate_number}")

# ==== TESTING USAGE ====
if __name__ == "__main__":
    plate = input("Enter plate number to mark as paid: ").strip().upper()
    mark_payment_success(plate)