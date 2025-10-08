from flask import Flask, request, jsonify, render_template
from datetime import datetime
import sqlite3

app = Flask(__name__)

# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect('feeder.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    db = get_db()
    logs = db.execute("SELECT * FROM feed_log ORDER BY timestamp DESC LIMIT 10").fetchall()
    return render_template('index.html', logs=logs)

# --- COMMAND API ---
@app.route('/api/command/<device_id>', methods=['GET'])
def get_command(device_id):
    db = get_db()
    cmd = db.execute("SELECT command FROM commands WHERE device_id=? LIMIT 1", (device_id,)).fetchone()
    if cmd:
        db.execute("DELETE FROM commands WHERE device_id=?", (device_id,))
        db.commit()
        return jsonify({"command": cmd['command']})
    return jsonify({"command": "none"})

@app.route('/api/send_command', methods=['POST'])
def send_command():
    data = request.json
    db = get_db()
    db.execute("INSERT INTO commands (device_id, command) VALUES (?, ?)", (data['device_id'], data['command']))
    db.commit()
    return jsonify({"status": "ok"})

# --- UPDATE STATUS ---
@app.route('/api/update', methods=['POST'])
def update_status():
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO feed_log (device_id, weight, level, timestamp) VALUES (?, ?, ?, ?)",
        (data['device_id'], data['weight'], data['level'], datetime.now())
    )
    db.commit()
    return jsonify({"status": "received"})

if __name__ == '__main__':
    app.run(debug=True)
