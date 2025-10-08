# ===============================
# Smart Pet Feeder Web Backend
# ===============================
# This Flask app handles:
#  - Feeding schedules
#  - Manual feed commands
#  - Camera control
#  - Sensor data display
#  - Communication with Raspberry Pi client
#  - Database storage (PostgreSQL on Render)
# ===============================

from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import db
from datetime import datetime
import os

# --------------------------------
# App Configuration
# --------------------------------
app = Flask(__name__)

# DATABASE_URL will be automatically provided by Render
# If not found (e.g., when testing locally), fallback to SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///feeder.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy (ORM for interacting with the database)
db.init_app(app)

# --------------------------------
# Database Models
# --------------------------------
# To avoid circular imports, models are placed in a separate file (models.py)
# Import them after initializing db
from models import Schedule, FeedLog, SensorData, Command

# Create tables (only runs if they don’t exist yet)
with app.app_context():
    db.create_all()


# --------------------------------
# 🏠 Home page — dashboard
# --------------------------------
@app.route('/')
def index():
    # Get all feeding schedules
    schedules = Schedule.query.all()
    # Get the latest sensor reading (for food level)
    latest_sensor = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    # Render dashboard
    return render_template('index.html', schedules=schedules, sensor=latest_sensor)


# --------------------------------
# 📅 Schedule management page
# --------------------------------
@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        # When form is submitted: create new schedule
        time = request.form['time']
        portion = request.form['portion']
        new_schedule = Schedule(time=time, portion=portion)
        db.session.add(new_schedule)
        db.session.commit()
        return redirect(url_for('schedule'))

    # When viewing: show all schedules
    schedules = Schedule.query.all()
    return render_template('schedule.html', schedules=schedules)


@app.route('/delete_schedule/<int:id>')
def delete_schedule(id):
    # Delete selected schedule
    s = Schedule.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return redirect(url_for('schedule'))


# --------------------------------
# 📜 Feeding logs page
# --------------------------------
@app.route('/logs')
def logs():
    logs = FeedLog.query.order_by(FeedLog.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)


# --------------------------------
# 📡 Sensor data page
# --------------------------------
@app.route('/sensors')
def sensors():
    data = SensorData.query.order_by(SensorData.timestamp.desc()).limit(10).all()
    return render_template('sensors.html', data=data)


# --------------------------------
# 🎥 Camera control page + API
# --------------------------------
@app.route('/camera')
def camera():
    # Basic page with ON/OFF buttons (handled in HTML)
    return render_template('camera.html')


@app.route('/api/camera/<action>')
def camera_control(action):
    # Accepts "on" or "off" from the dashboard
    if action in ['on', 'off']:
        cmd = Command(command=f'camera_{action}')
        db.session.add(cmd)
        db.session.commit()
        return jsonify({'status': f'Camera turned {action}'})
    return jsonify({'error': 'Invalid command'})


# --------------------------------
# 🧠 API for Raspberry Pi Client
# --------------------------------
# The Raspberry Pi will poll this endpoint to get pending commands.
@app.route('/api/get_command')
def get_command():
    cmd = Command.query.order_by(Command.id.asc()).first()
    if cmd:
        command_text = cmd.command
        db.session.delete(cmd)  # Remove command once retrieved
        db.session.commit()
        return jsonify({'command': command_text})
    return jsonify({'command': 'none'})  # No command waiting


# Pi uploads feeding log after each feeding
@app.route('/api/upload_log', methods=['POST'])
def upload_log():
    data = request.json
    new_log = FeedLog(amount=data.get('amount'), result=data.get('result'))
    db.session.add(new_log)
    db.session.commit()
    return jsonify({'status': 'log_saved'})


# Pi uploads food level (VL53L0X reading)
@app.route('/api/update_level', methods=['POST'])
def update_level():
    data = request.json
    new_data = SensorData(level=data.get('level'))
    db.session.add(new_data)
    db.session.commit()
    return jsonify({'status': 'level_updated'})


# --------------------------------
# 🍖 Manual Feed Command
# --------------------------------
@app.route('/feed_now', methods=['POST'])
def feed_now():
    portion = request.form['portion']
    # Create a new "feed" command for the Pi
    cmd = Command(command=f'feed:{portion}')
    db.session.add(cmd)
    db.session.commit()
    return redirect(url_for('index'))


# --------------------------------
# 🚀 Run locally
# --------------------------------
if __name__ == '__main__':
    app.run(debug=True)
