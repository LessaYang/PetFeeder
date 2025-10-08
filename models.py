# ===============================
# models.py
# ===============================
# This file defines all database tables (models)
# using SQLAlchemy ORM.
#
# Each model = 1 table in your PostgreSQL database.
# The Flask app (web + Raspberry Pi client) will
# read/write data through these models.
# ===============================

from database import db
from datetime import datetime

# --------------------------------
# 🕒 Feeding Schedule
# --------------------------------
class Schedule(db.Model):
    """
    Stores scheduled feeding times and portion sizes
    set by the user through the web dashboard.
    Raspberry Pi uses this info to feed at the right time.
    """
    id = db.Column(db.Integer, primary_key=True)  # unique row ID
    time = db.Column(db.String(10))               # feeding time (e.g., "08:00")
    portion = db.Column(db.Float)                 # portion size in grams
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Schedule {self.time} - {self.portion}g>"


# --------------------------------
# 📜 Feeding Log
# --------------------------------
class FeedLog(db.Model):
    """
    Records every feeding event that actually happened.
    Data comes from the Raspberry Pi after it dispenses food.
    """
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)                  # actual food dispensed (grams)
    result = db.Column(db.String(50))             # e.g. "success", "jammed", "manual"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FeedLog {self.amount}g @ {self.timestamp}>"


# --------------------------------
# 📡 Sensor Data
# --------------------------------
class SensorData(db.Model):
    """
    Stores data from sensors:
     - VL53L0X → estimates food left in container (%)
     - HX711   → actual food dispensed (if logged)
    The latest entry shows in the dashboard.
    """
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Float)                   # remaining food (%) or raw distance
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SensorData {self.level}% @ {self.timestamp}>"


# --------------------------------
# 🧠 Command Queue
# --------------------------------
class Command(db.Model):
    """
    Temporary queue for commands sent from the web app
    to the Raspberry Pi.
    Examples:
      - 'feed:30'  → feed 30 grams now
      - 'camera_on'
      - 'camera_off'
    Raspberry Pi periodically calls /api/get_command to check for new commands.
    After a command is read, it’s deleted from the database.
    """
    id = db.Column(db.Integer, primary_key=True)
    command = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Command {self.command}>"
