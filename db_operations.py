from datetime import datetime
from db_config import get_db_connection, release_db_connection

def add_parking_entry(plate_number):
    """Add a new parking entry"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO parking_entries (plate_number, entry_timestamp)
                VALUES (%s, %s)
                RETURNING id
            """, (plate_number, datetime.now()))
            entry_id = cur.fetchone()[0]
            conn.commit()
            return entry_id
    except Exception as e:
        print(f"Error adding parking entry: {e}")
        conn.rollback()
        return None
    finally:
        release_db_connection(conn)

def update_payment_status(plate_number, entry_timestamp, amount_paid):
    """Update payment status for a parking entry"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE parking_entries
                SET payment_status = TRUE,
                    payment_timestamp = %s,
                    amount_paid = %s
                WHERE plate_number = %s
                AND entry_timestamp = %s
                AND payment_status = FALSE
                RETURNING id
            """, (datetime.now(), amount_paid, plate_number, entry_timestamp))
            updated_id = cur.fetchone()
            conn.commit()
            return updated_id is not None
    except Exception as e:
        print(f"Error updating payment status: {e}")
        conn.rollback()
        return False
    finally:
        release_db_connection(conn)

def update_exit_timestamp(plate_number):
    """Update exit timestamp for the latest entry of a plate"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE parking_entries
                SET exit_timestamp = %s
                WHERE id = (
                    SELECT id FROM parking_entries
                    WHERE plate_number = %s
                    ORDER BY entry_timestamp DESC
                    LIMIT 1
                )
                RETURNING id
            """, (datetime.now(), plate_number))
            updated_id = cur.fetchone()
            conn.commit()
            return updated_id is not None
    except Exception as e:
        print(f"Error updating exit timestamp: {e}")
        conn.rollback()
        return False
    finally:
        release_db_connection(conn)

def add_alert(alert_type, plate_number, message):
    """Add a new alert to the system"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO alerts (alert_type, plate_number, message)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (alert_type, plate_number, message))
            alert_id = cur.fetchone()[0]
            conn.commit()
            return alert_id
    except Exception as e:
        print(f"Error adding alert: {e}")
        conn.rollback()
        return None
    finally:
        release_db_connection(conn)

def get_recent_alerts(limit=50):
    """Get recent alerts"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, alert_type, plate_number, message, timestamp, is_read
                FROM alerts
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
            alerts = cur.fetchall()
            return [{
                'id': alert[0],
                'alert_type': alert[1],
                'plate_number': alert[2],
                'message': alert[3],
                'timestamp': alert[4],
                'is_read': alert[5]
            } for alert in alerts]
    except Exception as e:
        print(f"Error getting alerts: {e}")
        return []
    finally:
        release_db_connection(conn)

def mark_alert_as_read(alert_id):
    """Mark an alert as read"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE alerts
                SET is_read = TRUE
                WHERE id = %s
                RETURNING id
            """, (alert_id,))
            updated_id = cur.fetchone()
            conn.commit()
            return updated_id is not None
    except Exception as e:
        print(f"Error marking alert as read: {e}")
        conn.rollback()
        return False
    finally:
        release_db_connection(conn)

def is_payment_complete(plate_number):
    """Check if payment is complete for the latest entry of a plate"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT payment_status
                FROM parking_entries
                WHERE plate_number = %s
                ORDER BY entry_timestamp DESC
                LIMIT 1
            """, (plate_number,))
            result = cur.fetchone()
            return result[0] if result else False
    except Exception as e:
        print(f"Error checking payment status: {e}")
        return False
    finally:
        release_db_connection(conn)

def get_last_unpaid_entry(plate_number):
    """Get the last unpaid entry for a plate"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, plate_number, entry_timestamp
                FROM parking_entries
                WHERE plate_number = %s
                AND payment_status = FALSE
                ORDER BY entry_timestamp DESC
                LIMIT 1
            """, (plate_number,))
            result = cur.fetchone()
            if result:
                return {
                    'id': result[0],
                    'plate_number': result[1],
                    'entry_timestamp': result[2]
                }
            return None
    except Exception as e:
        print(f"Error getting last unpaid entry: {e}")
        return None
    finally:
        release_db_connection(conn)

def get_parking_duration(entry_timestamp):
    """Calculate parking duration in minutes"""
    now = datetime.now()
    duration = now - entry_timestamp
    return int(duration.total_seconds() / 60)

def get_parking_history(plate_number, limit=10):
    """Get parking history for a plate number"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, plate_number, payment_status, entry_timestamp, 
                       exit_timestamp, payment_timestamp, amount_paid
                FROM parking_entries
                WHERE plate_number = %s
                ORDER BY entry_timestamp DESC
                LIMIT %s
            """, (plate_number, limit))
            results = cur.fetchall()
            return [{
                'id': row[0],
                'plate_number': row[1],
                'payment_status': row[2],
                'entry_timestamp': row[3],
                'exit_timestamp': row[4],
                'payment_timestamp': row[5],
                'amount_paid': row[6]
            } for row in results]
    except Exception as e:
        print(f"Error getting parking history: {e}")
        return []
    finally:
        release_db_connection(conn)

def get_recent_activities(limit=50):
    """Get recent parking activities including entries, exits, and payments"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, plate_number, payment_status, entry_timestamp,
                       exit_timestamp, payment_timestamp, amount_paid
                FROM parking_entries
                ORDER BY 
                    GREATEST(
                        entry_timestamp,
                        COALESCE(exit_timestamp, '1970-01-01'),
                        COALESCE(payment_timestamp, '1970-01-01')
                    ) DESC
                LIMIT %s
            """, (limit,))
            results = cur.fetchall()
            return [{
                'id': row[0],
                'plate_number': row[1],
                'payment_status': row[2],
                'entry_timestamp': row[3],
                'exit_timestamp': row[4],
                'payment_timestamp': row[5],
                'amount_paid': row[6]
            } for row in results]
    except Exception as e:
        print(f"Error getting recent activities: {e}")
        return []
    finally:
        release_db_connection(conn)

def get_daily_stats():
    """Get daily statistics"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get today's stats
            today = datetime.now().date()
            cur.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(CASE WHEN exit_timestamp IS NOT NULL THEN 1 END) as total_exits,
                    COUNT(CASE WHEN payment_status = TRUE THEN 1 END) as total_paid,
                    COALESCE(SUM(amount_paid), 0) as total_revenue,
                    COUNT(CASE WHEN exit_timestamp IS NULL THEN 1 END) as current_occupancy
                FROM parking_entries 
                WHERE DATE(entry_timestamp) = %s
            """, (today,))
            result = cur.fetchone()
            
            return {
                'total_entries': result[0],
                'total_exits': result[1],
                'total_paid': result[2],
                'total_revenue': float(result[3]),
                'current_occupancy': result[4]
            }
    except Exception as e:
        print(f"Error getting daily stats: {e}")
        return {}
    finally:
        release_db_connection(conn)

def get_hourly_occupancy():
    """Get hourly occupancy for the last 24 hours"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                WITH RECURSIVE hours AS (
                    SELECT date_trunc('hour', NOW() - interval '23 hours') as hour
                    UNION ALL
                    SELECT hour + interval '1 hour'
                    FROM hours
                    WHERE hour < date_trunc('hour', NOW())
                ),
                hourly_entries AS (
                    SELECT 
                        date_trunc('hour', entry_timestamp) as hour,
                        COUNT(*) as entries
                    FROM parking_entries
                    WHERE entry_timestamp >= NOW() - interval '24 hours'
                    GROUP BY 1
                ),
                hourly_exits AS (
                    SELECT 
                        date_trunc('hour', exit_timestamp) as hour,
                        COUNT(*) as exits
                    FROM parking_entries
                    WHERE exit_timestamp >= NOW() - interval '24 hours'
                    GROUP BY 1
                )
                SELECT 
                    hours.hour,
                    COALESCE(entries, 0) as entries,
                    COALESCE(exits, 0) as exits
                FROM hours
                LEFT JOIN hourly_entries ON hours.hour = hourly_entries.hour
                LEFT JOIN hourly_exits ON hours.hour = hourly_exits.hour
                ORDER BY hours.hour
            """)
            results = cur.fetchall()
            
            return [{
                'hour': result[0].strftime('%Y-%m-%d %H:%M:%S'),
                'entries': result[1],
                'exits': result[2]
            } for result in results]
    except Exception as e:
        print(f"Error getting hourly occupancy: {e}")
        return []
    finally:
        release_db_connection(conn)

def get_weekly_revenue():
    """Get daily revenue for the last 7 days"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                WITH RECURSIVE days AS (
                    SELECT date_trunc('day', NOW() - interval '6 days') as day
                    UNION ALL
                    SELECT day + interval '1 day'
                    FROM days
                    WHERE day < date_trunc('day', NOW())
                )
                SELECT 
                    days.day,
                    COALESCE(SUM(amount_paid), 0) as revenue,
                    COUNT(*) as transactions
                FROM days
                LEFT JOIN parking_entries ON date_trunc('day', payment_timestamp) = days.day
                GROUP BY days.day
                ORDER BY days.day
            """)
            results = cur.fetchall()
            
            return [{
                'date': result[0].strftime('%Y-%m-%d'),
                'revenue': float(result[1]),
                'transactions': result[2]
            } for result in results]
    except Exception as e:
        print(f"Error getting weekly revenue: {e}")
        return []
    finally:
        release_db_connection(conn)

def get_peak_hours():
    """Get peak hours analysis"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    EXTRACT(HOUR FROM entry_timestamp) as hour,
                    COUNT(*) as entries
                FROM parking_entries
                WHERE entry_timestamp >= NOW() - interval '7 days'
                GROUP BY 1
                ORDER BY 2 DESC
                LIMIT 5
            """)
            results = cur.fetchall()
            
            return [{
                'hour': int(result[0]),
                'entries': result[1]
            } for result in results]
    except Exception as e:
        print(f"Error getting peak hours: {e}")
        return []
    finally:
        release_db_connection(conn) 