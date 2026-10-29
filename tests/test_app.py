import csv
import io
import tempfile
import unittest
from pathlib import Path

import app as classroom_app


class ClassroomAppTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parents[1] / ".test-tmp"
        temp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=temp_root)
        classroom_app.DB_PATH = Path(self.temp_dir.name) / "test.db"
        classroom_app.active_monitor = None
        classroom_app.active_session_id = None
        classroom_app.init_db()
        self.client = classroom_app.app.test_client()

    def tearDown(self):
        if classroom_app.active_monitor:
            classroom_app.active_monitor.stop()
        classroom_app.active_monitor = None
        classroom_app.active_session_id = None
        self.temp_dir.cleanup()

    def add_participant(self, name="Alex Learner", student_id="STU-1"):
        return self.client.post("/api/roster", json={"name": name, "id": student_id})

    def test_dashboard_and_empty_state_load(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["roster"], [])
        self.assertIsNone(response.get_json()["session"])

    def test_roster_validation_and_duplicate_id(self):
        self.assertEqual(self.add_participant(name=" ").status_code, 400)
        self.assertEqual(self.add_participant().status_code, 200)
        self.assertEqual(self.add_participant(name="Second learner").status_code, 409)

    def test_manual_attendance_session_and_csv_export(self):
        self.assertEqual(self.add_participant().status_code, 200)
        started = self.client.post("/api/sessions/start", json={"title": "Biology", "camera": False, "audio": False})
        self.assertEqual(started.status_code, 200)
        session_id = started.get_json()["session_id"]

        check_in = self.client.post("/api/attendance", json={"student_id": "STU-1", "mode": "in"})
        self.assertEqual(check_in.status_code, 200)
        self.assertEqual(self.client.post("/api/attendance", json={"student_id": "STU-1", "mode": "in"}).status_code, 400)
        self.assertEqual(self.client.post("/api/sessions/end").status_code, 200)

        details = self.client.get("/api/sessions/" + session_id).get_json()
        self.assertIsNotNone(details["ended_at"])
        self.assertEqual(details["attendance"][0]["check_out"], details["ended_at"])
        export = self.client.get("/api/sessions/" + session_id + "/export.csv")
        rows = list(csv.reader(io.StringIO(export.get_data(as_text=True).lstrip("\ufeff"))))
        self.assertEqual(rows[1][3:5], ["STU-1", "Alex Learner"])

    def test_invalid_session_transitions_return_clear_errors(self):
        self.assertEqual(self.client.post("/api/sessions/end").status_code, 409)
        self.assertEqual(self.client.post("/api/attendance", json={"student_id": "STU-1", "mode": "in"}).status_code, 409)
        self.assertEqual(self.client.post("/api/sessions/mode", json={"mode": "invalid"}).status_code, 400)

    def test_startup_closes_sessions_left_open_by_a_process_exit(self):
        with classroom_app.connect() as db:
            db.execute("INSERT INTO students(id, name, token, created_at) VALUES(?, ?, ?, ?)", ("STU-1", "Alex Learner", "token", classroom_app.now_utc()))
            db.execute("INSERT INTO sessions(id, title, started_at) VALUES(?, ?, ?)", ("old-session", "Old session", classroom_app.now_utc()))
            db.execute("INSERT INTO attendance(session_id, student_id, check_in) VALUES(?, ?, ?)", ("old-session", "STU-1", classroom_app.now_utc()))

        classroom_app.init_db()
        session = self.client.get("/api/sessions/old-session").get_json()
        self.assertIsNotNone(session["ended_at"])
        self.assertEqual(session["attendance"][0]["check_out"], session["ended_at"])


if __name__ == "__main__":
    unittest.main()
