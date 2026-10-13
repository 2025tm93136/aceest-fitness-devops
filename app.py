"""ACEest Fitness & Gym - Flask service.

Web/API port of the ACEest Tkinter desktop app (versions 1.0 - 3.2.4):
programs, clients, calorie estimation, weekly adherence, workouts and membership.
"""
import os
import sqlite3
from datetime import date

from flask import Flask, g, jsonify, request

APP_VERSION = "1.0.0"

PROGRAMS = {
    "FL": {
        "name": "Fat Loss",
        "workout": [
            "Mon: 5x5 Back Squat + AMRAP",
            "Tue: EMOM 20min Assault Bike",
            "Wed: Bench Press + 21-15-9",
            "Thu: 10RFT Deadlifts/Box Jumps",
            "Fri: 30min Active Recovery",
        ],
        "diet": [
            "B: 3 Egg Whites + Oats Idli",
            "L: Grilled Chicken + Brown Rice",
            "D: Fish Curry + Millet Roti",
        ],
        "target_kcal": 2000,
        "calorie_factor": 22,
    },
    "MG": {
        "name": "Muscle Gain",
        "workout": [
            "Mon: Squat 5x5",
            "Tue: Bench 5x5",
            "Wed: Deadlift 4x6",
            "Thu: Front Squat 4x8",
            "Fri: Incline Press 4x10",
            "Sat: Barbell Rows 4x10",
        ],
        "diet": [
            "B: 4 Eggs + PB Oats",
            "L: Chicken Biryani (250g Chicken)",
            "D: Mutton Curry + Jeera Rice",
        ],
        "target_kcal": 3200,
        "calorie_factor": 35,
    },
    "BG": {
        "name": "Beginner",
        "workout": [
            "Circuit Training: Air Squats, Ring Rows, Push-ups",
            "Focus: Technique Mastery & Form (90% Threshold)",
        ],
        "diet": [
            "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati",
            "Protein: 120g/day",
        ],
        "target_kcal": 2600,
        "calorie_factor": 26,
    },
}

WORKOUT_TYPES = {"Strength", "Hypertrophy", "Cardio", "Mobility"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER,
    weight REAL,
    program TEXT,
    calories INTEGER,
    membership_status TEXT DEFAULT 'Active',
    membership_end TEXT
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week TEXT NOT NULL,
    adherence INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    workout_type TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    notes TEXT
);
"""


def calculate_calories(weight_kg, program_code):
    """Daily calorie estimate = body weight (kg) x program calorie factor."""
    if program_code not in PROGRAMS:
        raise ValueError(f"Unknown program: {program_code}")
    if weight_kg is None or weight_kg <= 0:
        raise ValueError("Weight must be a positive number")
    return int(weight_kg * PROGRAMS[program_code]["calorie_factor"])


def calculate_bmi(weight_kg, height_cm):
    if weight_kg <= 0 or height_cm <= 0:
        raise ValueError("Weight and height must be positive")
    return round(weight_kg / (height_cm / 100) ** 2, 1)


def is_int(value):
    """True for real integers; JSON booleans are rejected even though bool subclasses int."""
    return isinstance(value, int) and not isinstance(value, bool)


def membership_is_active(status, end_date, today=None):
    if status != "Active":
        return False
    if not end_date:
        return True
    return date.fromisoformat(end_date) >= (today or date.today())


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get("ACEEST_DB", "aceest_fitness.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        get_db().executescript(SCHEMA)

    def error(message, status=400):
        return jsonify({"error": message}), status

    def find_client(name):
        return get_db().execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()

    @app.get("/")
    def index():
        return jsonify({"service": "ACEest Fitness & Gym", "version": APP_VERSION})

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/programs")
    def list_programs():
        return jsonify({code: p["name"] for code, p in PROGRAMS.items()})

    @app.get("/programs/<code>")
    def get_program(code):
        program = PROGRAMS.get(code.upper())
        if not program:
            return error("Program not found", 404)
        return jsonify({"code": code.upper(), **program})

    @app.post("/bmi")
    def bmi():
        data = request.get_json(silent=True) or {}
        try:
            value = calculate_bmi(float(data.get("weight", 0)), float(data.get("height", 0)))
        except (TypeError, ValueError) as exc:
            return error(str(exc))
        return jsonify({"bmi": value})

    @app.get("/clients")
    def list_clients():
        rows = get_db().execute("SELECT * FROM clients ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients")
    def create_client():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        program = (data.get("program") or "").upper()
        if not name:
            return error("Client name is required")
        try:
            weight = float(data.get("weight", 0))
            calories = calculate_calories(weight, program)
        except (TypeError, ValueError) as exc:
            return error(str(exc))
        if find_client(name):
            return error("Client already exists", 409)
        db = get_db()
        db.execute(
            "INSERT INTO clients (name, age, weight, program, calories, membership_end) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, data.get("age"), weight, program, calories, data.get("membership_end")),
        )
        db.commit()
        return jsonify(dict(find_client(name))), 201

    @app.get("/clients/<name>")
    def get_client(name):
        client = find_client(name)
        if not client:
            return error("Client not found", 404)
        return jsonify(dict(client))

    @app.delete("/clients/<name>")
    def delete_client(name):
        if not find_client(name):
            return error("Client not found", 404)
        db = get_db()
        for table, col in (("progress", "client_name"), ("workouts", "client_name"), ("clients", "name")):
            db.execute(f"DELETE FROM {table} WHERE {col}=?", (name,))
        db.commit()
        return "", 204

    @app.get("/clients/<name>/membership")
    def membership(name):
        client = find_client(name)
        if not client:
            return error("Client not found", 404)
        return jsonify({
            "status": client["membership_status"],
            "end": client["membership_end"],
            "active": membership_is_active(client["membership_status"], client["membership_end"]),
        })

    @app.post("/clients/<name>/progress")
    def add_progress(name):
        if not find_client(name):
            return error("Client not found", 404)
        data = request.get_json(silent=True) or {}
        week = data.get("week")
        adherence = data.get("adherence")
        if not week or not is_int(adherence) or not 0 <= adherence <= 100:
            return error("week is required and adherence must be an integer 0-100")
        db = get_db()
        db.execute(
            "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
            (name, week, adherence),
        )
        db.commit()
        return jsonify({"week": week, "adherence": adherence}), 201

    @app.get("/clients/<name>/progress")
    def get_progress(name):
        if not find_client(name):
            return error("Client not found", 404)
        rows = get_db().execute(
            "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id", (name,)
        ).fetchall()
        entries = [dict(r) for r in rows]
        average = round(sum(e["adherence"] for e in entries) / len(entries), 1) if entries else None
        return jsonify({"entries": entries, "average_adherence": average})

    @app.post("/clients/<name>/workouts")
    def add_workout(name):
        if not find_client(name):
            return error("Client not found", 404)
        data = request.get_json(silent=True) or {}
        workout_type = data.get("type")
        duration = data.get("duration_min")
        if workout_type not in WORKOUT_TYPES:
            return error(f"type must be one of {sorted(WORKOUT_TYPES)}")
        if not is_int(duration) or duration <= 0:
            return error("duration_min must be a positive integer")
        workout_date = data.get("date") or date.today().isoformat()
        db = get_db()
        db.execute(
            "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, workout_date, workout_type, duration, data.get("notes", "")),
        )
        db.commit()
        return jsonify({"date": workout_date, "type": workout_type, "duration_min": duration}), 201

    @app.get("/clients/<name>/workouts")
    def get_workouts(name):
        if not find_client(name):
            return error("Client not found", 404)
        rows = get_db().execute(
            "SELECT date, workout_type, duration_min, notes FROM workouts "
            "WHERE client_name=? ORDER BY date DESC",
            (name,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
