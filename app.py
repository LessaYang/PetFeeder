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
#  - Dynamic ngrok camera URL updates
# ===============================

from flask import Flask, render_template, request, redirect, url_for, jsonify
from database import db
from datetime import datetime
import os
import socket

# --------------------------------
# App Configuration
# --------------------------------
app = Flask(__name__)

# DATABASE_URL (Render will inject automatically)
# Fallback to local SQLite for testing
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///feeder.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db.init_app(app)

# Import models (after db.init_app to avoid circular imports)
from models import Schedule, FeedLog, SensorData, Command

# Create tables if missing
with app.app_context():
    db.create_all()

# --------------------------------
# 🔗 Store current ngrok link (updated by Pi)
# --------------------------------
current_ngrok_url = None


# --------------------------------
# 🏠 Dashboard
# --------------------------------
@app.route('/')
def index():
    schedules = Schedule.query.all()
    latest_sensor = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    return render_template('index.html', schedules=schedules, sensor=latest_sensor)


# --------------------------------
# 📅 Schedule management
# --------------------------------
@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        time_str = request.form['time']
        portion = request.form['portion']
        new_schedule = Schedule(time=time_str, portion=portion)
        db.session.add(new_schedule)
        db.session.commit()
        return redirect(url_for('schedule'))
    schedules = Schedule.query.all()
    return render_template('schedule.html', schedules=schedules)


@app.route('/delete_schedule/<int:id>')
def delete_schedule(id):
    s = Schedule.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return redirect(url_for('schedule'))

# --------------------------------
# 🗓️ API: schedule fetch for Pi client
# --------------------------------
@app.route('/api/get_schedule', methods=['GET'])
def get_schedule():
    schedules = Schedule.query.all()
    schedule_list = [{"time": s.time, "portion": s.portion} for s in schedules]
    return jsonify({"schedule": schedule_list})

# --------------------------------
# 📜 Feeding logs
# --------------------------------
@app.route('/logs')
def logs():
    logs = FeedLog.query.order_by(FeedLog.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)


# --------------------------------
# 📡 Sensor data
# --------------------------------
@app.route('/sensors')
def sensors():
    data = SensorData.query.order_by(SensorData.timestamp.desc()).limit(10).all()
    return render_template('sensors.html', data=data)


# --------------------------------
# 🎥 Camera control + ngrok integration
# --------------------------------
@app.route('/camera')
def camera():
    # Try to get local Pi IP (for LAN fallback)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    # Default local stream (if ngrok not yet reported)
    fallback_url = f"http://{local_ip}:8080/?action=stream"
    stream_url = current_ngrok_url or fallback_url

    return render_template('camera.html', title="Camera", stream_url=stream_url)


# ---------- 🧠 API: ngrok updates ----------
@app.route('/api/update_ngrok', methods=['POST'])
def update_ngrok():
    """Pi client sends its current ngrok URL here."""
    global current_ngrok_url
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url'"}), 400
    current_ngrok_url = data["url"]
    print(f"[INFO] Updated ngrok URL: {current_ngrok_url}")
    return jsonify({"status": "ok"}), 200


@app.route('/api/get_ngrok', methods=['GET'])
def get_ngrok():
    """Web dashboard fetches the latest ngrok link."""
    return jsonify({"url": current_ngrok_url})


# ---------- 🧠 API: Pi Client ----------
@app.route('/api/get_command')
def get_command():
    cmd = Command.query.order_by(Command.id.asc()).first()
    if cmd:
        command_text = cmd.command
        db.session.delete(cmd)
        db.session.commit()
        return jsonify({'command': command_text})
    return jsonify({'command': 'none'})


@app.route('/api/upload_log', methods=['POST'])
def upload_log():
    data = request.json
    new_log = FeedLog(amount=data.get('amount'), result=data.get('result'))
    db.session.add(new_log)
    db.session.commit()
    return jsonify({'status': 'log_saved'})


@app.route('/api/update_level', methods=['POST'])
def update_level():
    data = request.json
    new_data = SensorData(level=data.get('level'))
    db.session.add(new_data)
    db.session.commit()
    return jsonify({'status': 'level_updated'})


# --------------------------------
# 🍖 Manual feed
# --------------------------------
@app.route('/feed_now', methods=['POST'])
def feed_now():
    portion = request.form['portion']
    cmd = Command(command=f'feed:{portion}')
    db.session.add(cmd)
    db.session.commit()
    return redirect(url_for('index'))


# --------------------------------
# 🚀 Run locally
# --------------------------------
if __name__ == '__main__':
    app.run(debug=True)
