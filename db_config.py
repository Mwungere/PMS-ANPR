import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_NAME = os.getenv('DB_NAME', 'parking_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# Create a connection pool
connection_pool = pool.SimpleConnectionPool(
    1,  # minconn
    10, # maxconn
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

def get_db_connection():
    """Get a connection from the pool"""
    return connection_pool.getconn()

def release_db_connection(conn):
    """Release a connection back to the pool"""
    connection_pool.putconn(conn)

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Create parking_entries table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS parking_entries (
                    id SERIAL PRIMARY KEY,
                    plate_number VARCHAR(10) NOT NULL,
                    payment_status BOOLEAN DEFAULT FALSE,
                    entry_timestamp TIMESTAMP NOT NULL,
                    exit_timestamp TIMESTAMP,
                    payment_timestamp TIMESTAMP,
                    amount_paid DECIMAL(10,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create index on plate_number for faster lookups
                CREATE INDEX IF NOT EXISTS idx_plate_number ON parking_entries(plate_number);
                
                -- Create index on payment_status for faster filtering
                CREATE INDEX IF NOT EXISTS idx_payment_status ON parking_entries(payment_status);

                -- Create alerts table for unauthorized attempts and other events
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    alert_type VARCHAR(50) NOT NULL,
                    plate_number VARCHAR(10),
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_read BOOLEAN DEFAULT FALSE
                );

                -- Create index on alert timestamp for faster retrieval
                CREATE INDEX IF NOT EXISTS idx_alert_timestamp ON alerts(timestamp);
            """)
        conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    init_db() 