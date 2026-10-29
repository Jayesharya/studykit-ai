import csv
import io
import os
import secrets
import sqlite3
import sys
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

if sys.version_info < (3, 8):
    raise RuntimeError("Python 3.8 or newer is required.")

ROOT = Path(__file__).resolve().parent
INSTANCE = ROOT / "instance"
INSTANCE.mkdir(exist_ok=True)
DB_PATH = INSTANCE / "classroom.db"

from classroom_agent.agent import build_insights
from classroom_agent.monitor import ClassroomMonitor

app = Flask(__name__, instance_path=str(INSTANCE), template_folder="classroom_agent/templates", static_folder="classroom_agent/static")
state_lock = threading.RLock()
active_monitor = None
active_session_id = None


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    db = sqlite3.connect(str(DB_PATH), timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys = ON")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                camera_enabled INTEGER NOT NULL DEFAULT 0,
                audio_enabled INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS attendance (
                session_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT,
                PRIMARY KEY (session_id, student_id)
            );
            CREATE TABLE IF NOT EXISTS activity_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                motion REAL,
                audio REAL
            );
            CREATE INDEX IF NOT EXISTS idx_activity_session_time
                ON activity_samples(session_id, captured_at);
        """)


def mark_attendance(session_id, student_id, mode):
    stamp = now_utc()
    with connect() as db:
        session = db.execute(
            "SELECT ended_at FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session or session["ended_at"]:
            return False, "No active session."
        student = db.execute(
            "SELECT id FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if not student:
            return False, "This participant is not on the local roster."
        row = db.execute(
            "SELECT check_out FROM attendance WHERE session_id=? AND student_id=?",
            (session_id, student_id),
        ).fetchone()
        if mode == "in":
            if row:
                return False, "Already checked in for this session."
            db.execute(
                "INSERT INTO attendance(session_id, student_id, check_in) VALUES(?, ?, ?)",
                (session_id, student_id, stamp),
            )
            return True, "Check-in recorded."
        if mode == "out":
            if not row:
                return False, "Check-in is needed before check-out."
            if row["check_out"]:
                return False, "Already checked out."
            db.execute(
                "UPDATE attendance SET check_out=? WHERE session_id=? AND student_id=?",
                (stamp, session_id, student_id),
            )
            return True, "Check-out recorded."
    return False, "Choose check-in or check-out."


def mark_qr(session_id, token, mode):
    with connect() as db:
        row = db.execute("SELECT id FROM students WHERE token=?", (token,)).fetchone()
    if not row:
        return
    mark_attendance(session_id, row["id"], mode)


def record_sample(session_id, sample):
    motion = sample.get("motion")
    audio = sample.get("audio")
    if motion is None and audio is None:
        return
    with connect() as db:
        live = db.execute(
            "SELECT ended_at FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if live and not live["ended_at"]:
            db.execute(
                "INSERT INTO activity_samples(session_id, captured_at, motion, audio) VALUES(?, ?, ?, ?)",
                (session_id, now_utc(), motion, audio),
            )


def session_payload(session_id):
    with connect() as db:
        session = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not session:
            return None
        attendance = db.execute("""
            SELECT a.student_id, s.name, a.check_in, a.check_out
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.session_id=? ORDER BY a.check_in
        """, (session_id,)).fetchall()
        samples = db.execute("""
            SELECT captured_at, motion, audio FROM activity_samples
            WHERE session_id=? ORDER BY captured_at DESC LIMIT 60
        """, (session_id,)).fetchall()
        roster_count = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    payload = dict(session)
    payload["attendance"] = [dict(row) for row in attendance]
    payload["samples"] = [dict(row) for row in reversed(samples)]
    payload["present_count"] = sum(1 for row in attendance if not row["check_out"])
    payload["roster_count"] = roster_count
    payload["insights"] = build_insights(payload["samples"], payload["present_count"], roster_count)
    return payload


def roster_payload():
    with connect() as db:
        rows = db.execute("SELECT id, name, created_at FROM students ORDER BY name").fetchall()
    return [dict(row) for row in rows]


def monitor_status():
    with state_lock:
        current = active_monitor
    return current.status() if current else {"camera": "off", "audio": "off", "scanner_mode": "in"}


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    with connect() as db:
        active = db.execute(
            "SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        history = db.execute("""
            SELECT id, title, started_at, ended_at FROM sessions
            ORDER BY started_at DESC LIMIT 10
        """).fetchall()
    current = session_payload(active["id"]) if active else None
    return jsonify({
        "roster": roster_payload(),
        "session": current,
        "history": [dict(row) for row in history],
        "devices": monitor_status(),
    })


@app.post("/api/roster")
def add_student():
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()[:80]
    student_id = str(body.get("id", "")).strip()[:32] or ("STU-" + secrets.token_hex(3).upper())
    if not name:
        return jsonify(error="Enter a participant name."), 400
    try:
        with connect() as db:
            db.execute(
                "INSERT INTO students(id, name, token, created_at) VALUES(?, ?, ?, ?)",
                (student_id, name, secrets.token_urlsafe(18), now_utc()),
            )
    except sqlite3.IntegrityError:
        return jsonify(error="That participant ID is already on the local roster."), 409
    return jsonify(ok=True, student_id=student_id)


@app.post("/api/sessions/start")
def start_session():
    global active_monitor, active_session_id
    body = request.get_json(silent=True) or {}
    title = str(body.get("title", "")).strip()[:100] or "Class session"
    use_camera = bool(body.get("camera"))
    use_audio = bool(body.get("audio"))
    with state_lock:
        if active_session_id:
            return jsonify(error="End the current session before starting another."), 409
        session_id = secrets.token_hex(8)
        stamp = now_utc()
        with connect() as db:
            db.execute(
                "INSERT INTO sessions(id, title, started_at, camera_enabled, audio_enabled) VALUES(?, ?, ?, ?, ?)",
                (session_id, title, stamp, int(use_camera), int(use_audio)),
            )
        monitor = ClassroomMonitor(
            on_qr=lambda token, mode: mark_qr(session_id, token, mode),
            on_sample=lambda values: record_sample(session_id, values),
            camera_enabled=use_camera,
            audio_enabled=use_audio,
        )
        active_monitor = monitor
        active_session_id = session_id
        monitor.start()
    return jsonify(ok=True, session_id=session_id)


@app.post("/api/sessions/end")
def end_session():
    global active_monitor, active_session_id
    with state_lock:
        session_id = active_session_id
        monitor = active_monitor
        if not session_id:
            return jsonify(error="There is no active session."), 409
        if monitor:
            monitor.stop()
        stamp = now_utc()
        with connect() as db:
            db.execute("UPDATE sessions SET ended_at=? WHERE id=?", (stamp, session_id))
            db.execute(
                "UPDATE attendance SET check_out=? WHERE session_id=? AND check_out IS NULL",
                (stamp, session_id),
            )
        active_monitor = None
        active_session_id = None
    return jsonify(ok=True)


@app.post("/api/sessions/mode")
def scanner_mode():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode")
    if mode not in ("in", "out"):
        return jsonify(error="Mode must be check-in or check-out."), 400
    with state_lock:
        if not active_monitor:
            return jsonify(error="Start a session first."), 409
        active_monitor.set_mode(mode)
    return jsonify(ok=True, mode=mode)


@app.post("/api/attendance")
def manual_attendance():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode")
    student_id = str(body.get("student_id", ""))
    if mode not in ("in", "out"):
        return jsonify(error="Mode must be check-in or check-out."), 400
    with state_lock:
        session_id = active_session_id
    if not session_id:
        return jsonify(error="Start a session first."), 409
    ok, message = mark_attendance(session_id, student_id, mode)
    return (jsonify(ok=ok, message=message), 200 if ok else 400)


@app.get("/api/roster/<student_id>/qr")
def student_qr(student_id):
    with connect() as db:
        row = db.execute("SELECT name, token FROM students WHERE id=?", (student_id,)).fetchone()
    if not row:
        return jsonify(error="Participant not found."), 404
    try:
        import qrcode
        image = qrcode.make(row["token"])
    except ImportError:
        return jsonify(error="Install the QR package from requirements.txt to generate badges."), 503
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    stream.seek(0)
    return send_file(stream, mimetype="image/png", download_name="participant-badge.png")


@app.get("/api/sessions/<session_id>/export.csv")
def export_session(session_id):
    with connect() as db:
        session = db.execute("SELECT title, started_at, ended_at FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not session:
            return jsonify(error="Session not found."), 404
        rows = db.execute("""
            SELECT s.id, s.name, a.check_in, a.check_out
            FROM attendance a JOIN students s ON s.id=a.student_id
            WHERE a.session_id=? ORDER BY s.name
        """, (session_id,)).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["session_title", "session_started_at", "session_ended_at", "participant_id", "participant_name", "check_in_utc", "check_out_utc"])
    for row in rows:
        writer.writerow([session["title"], session["started_at"], session["ended_at"] or "", row["id"], row["name"], row["check_in"], row["check_out"] or ""])
    data = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    return send_file(data, mimetype="text/csv", as_attachment=True, download_name="attendance-session.csv")


@app.get("/api/sessions/<session_id>")
def session_details(session_id):
    payload = session_payload(session_id)
    if not payload:
        return jsonify(error="Session not found."), 404
    return jsonify(payload)


if __name__ == "__main__":
    init_db()
    print("Local classroom dashboard: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False, threaded=True)