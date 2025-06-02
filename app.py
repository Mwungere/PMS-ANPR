from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from db_operations import (
    get_recent_activities,
    get_recent_alerts,
    mark_alert_as_read,
    get_daily_stats,
    get_hourly_occupancy,
    get_weekly_revenue
)
from datetime import datetime, timedelta
import json
from threading import Lock
from decimal import Decimal

app = Flask(__name__)
app.config['SECRET_KEY'] = 'parking_management_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Thread handling
thread = None
thread_lock = Lock()

def serialize_datetime(obj):
    """Helper function to serialize datetime objects"""
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    return obj

def serialize_decimal(obj):
    """Helper function to serialize Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj

def format_activities(activities):
    """Format activities data for JSON serialization"""
    formatted = []
    for activity in activities:
        formatted_activity = activity.copy()
        formatted_activity['entry_timestamp'] = serialize_datetime(activity['entry_timestamp'])
        if activity.get('exit_timestamp'):
            formatted_activity['exit_timestamp'] = serialize_datetime(activity['exit_timestamp'])
        if activity.get('payment_timestamp'):
            formatted_activity['payment_timestamp'] = serialize_datetime(activity['payment_timestamp'])
        if activity.get('amount_paid'):
            formatted_activity['amount_paid'] = serialize_decimal(activity['amount_paid'])
        formatted.append(formatted_activity)
    return formatted

def format_alerts(alerts):
    """Format alerts data for JSON serialization"""
    formatted = []
    for alert in alerts:
        formatted_alert = alert.copy()
        formatted_alert['timestamp'] = serialize_datetime(alert['timestamp'])
        formatted.append(formatted_alert)
    return formatted

def format_stats(stats):
    """Format stats data for JSON serialization"""
    if not stats:
        return {}
    formatted_stats = stats.copy()
    for key, value in formatted_stats.items():
        if isinstance(value, Decimal):
            formatted_stats[key] = float(value)
    return formatted_stats

def background_task():
    """Background task to emit updates to connected clients"""
    while True:
        try:
            # Get and format activities
            activities = get_recent_activities(5)
            formatted_activities = format_activities(activities)
            socketio.emit('new_activities', formatted_activities)
            
            # Get and format alerts
            alerts = get_recent_alerts(5)
            formatted_alerts = format_alerts(alerts)
            socketio.emit('new_alerts', formatted_alerts)
            
            # Get and format stats
            stats = get_daily_stats()
            formatted_stats = format_stats(stats)
            socketio.emit('stats_update', formatted_stats)
            
            # Get and format occupancy data
            occupancy_data = get_hourly_occupancy()
            formatted_occupancy = []
            for entry in occupancy_data:
                formatted_entry = entry.copy()
                formatted_entry['hour'] = serialize_datetime(entry['hour']) if isinstance(entry['hour'], datetime) else entry['hour']
                for key, value in formatted_entry.items():
                    if isinstance(value, Decimal):
                        formatted_entry[key] = float(value)
                formatted_occupancy.append(formatted_entry)
            socketio.emit('occupancy_update', formatted_occupancy)
            
        except Exception as e:
            print(f"Error in background task: {e}")
            import traceback
            print(traceback.format_exc())
            
        socketio.sleep(5)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/activities')
def get_activities():
    activities = get_recent_activities(50)
    return jsonify(format_activities(activities))

@app.route('/api/alerts')
def get_alerts():
    alerts = get_recent_alerts(50)
    return jsonify(format_alerts(alerts))

@app.route('/api/mark-alert-read/<int:alert_id>')
def mark_alert_read(alert_id):
    success = mark_alert_as_read(alert_id)
    return jsonify({'success': success})

@app.route('/api/stats/daily')
def daily_stats():
    stats = get_daily_stats()
    return jsonify(format_stats(stats))

@app.route('/api/stats/occupancy')
def hourly_occupancy():
    stats = get_hourly_occupancy()
    formatted_stats = []
    for entry in stats:
        formatted_entry = entry.copy()
        formatted_entry['hour'] = serialize_datetime(entry['hour']) if isinstance(entry['hour'], datetime) else entry['hour']
        for key, value in formatted_entry.items():
            if isinstance(value, Decimal):
                formatted_entry[key] = float(value)
        formatted_stats.append(formatted_entry)
    return jsonify(formatted_stats)

@app.route('/api/stats/revenue')
def weekly_revenue():
    stats = get_weekly_revenue()
    formatted_stats = []
    for entry in stats:
        formatted_entry = entry.copy()
        formatted_entry['date'] = serialize_datetime(entry['date']) if isinstance(entry['date'], datetime) else entry['date']
        formatted_entry['revenue'] = serialize_decimal(entry['revenue'])
        formatted_stats.append(formatted_entry)
    return jsonify(formatted_stats)

@socketio.on('connect')
def handle_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_task)
    print('Client connected')

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True) 