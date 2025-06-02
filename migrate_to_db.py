import csv
from datetime import datetime
from db_operations import add_parking_entry, update_payment_status

def migrate_csv_to_db():
    """Migrate data from plates_log.csv to PostgreSQL database"""
    try:
        with open('plates_log.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert timestamp strings to datetime objects
                entry_timestamp = datetime.strptime(row['Timestamp'], '%Y-%m-%d %H:%M:%S')
                payment_timestamp = None
                if row.get('Payment Timestamp'):
                    payment_timestamp = datetime.strptime(row['Payment Timestamp'], '%Y-%m-%d %H:%M:%S')
                
                # Add entry to database
                entry_id = add_parking_entry(row['Plate Number'])
                
                # If payment was made, update payment status
                if row['Payment Status'] == '1' and payment_timestamp:
                    update_payment_status(
                        row['Plate Number'],
                        entry_timestamp,
                        None  # Amount paid not available in CSV
                    )
                
                print(f"Migrated entry for plate {row['Plate Number']}")
        
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate_csv_to_db() 