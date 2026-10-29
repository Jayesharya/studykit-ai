import threading
import time


class ClassroomMonitor:
    """Read-only device monitor. Frames and audio samples stay in memory and are discarded."""

    def __init__(self, on_qr, on_sample, camera_enabled=False, audio_enabled=False):
        self.on_qr = on_qr
        self.on_sample = on_sample
        self.camera_enabled = camera_enabled
        self.audio_enabled = audio_enabled
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.mode = "in"
        self.camera_status = "starting" if camera_enabled else "off"
        self.audio_status = "starting" if audio_enabled else "off"
        self.threads = []

    def start(self):
        if self.camera_enabled:
            self.threads.append(threading.Thread(target=self._camera_loop, daemon=True))
        if self.audio_enabled:
            self.threads.append(threading.Thread(target=self._audio_loop, daemon=True))
        for thread in self.threads:
            thread.start()

    def stop(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=2)

    def set_mode(self, mode):
        with self.lock:
            self.mode = mode

    def get_mode(self):
        with self.lock:
            return self.mode

    def status(self):
        return {
            "camera": self.camera_status,
            "audio": self.audio_status,
            "scanner_mode": self.get_mode(),
        }

    def _camera_loop(self):
        try:
            import cv2
            import numpy as np
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                self.camera_status = "unavailable"
                return
            self.camera_status = "on"
            detector = cv2.QRCodeDetector()
            previous = None
            qr_candidates = {}
            motion_window = []
            last_sample = time.monotonic()
            while not self.stop_event.is_set():
                ok, frame = camera.read()
                if not ok:
                    self.camera_status = "camera read failed"
                    time.sleep(0.5)
                    continue
                text, points, _ = detector.detectAndDecode(frame)
                now = time.monotonic()
                # Require repeated observations over several seconds so a
                # one-frame decode or passing badge does not mark attendance.
                seen = text.strip() if text else None
                for key in list(qr_candidates):
                    if key != seen and now - qr_candidates[key]["last"] > 7:
                        del qr_candidates[key]
                if seen:
                    candidate = qr_candidates.get(seen)
                    if candidate is not None and now - candidate["last"] > 7:
                        del qr_candidates[seen]
                        candidate = None
                    if candidate is None:
                        qr_candidates[seen] = {"first": now, "last": now, "hits": 1, "mode": None}
                    else:
                        if now - candidate["last"] >= 1.25:
                            candidate["hits"] += 1
                            candidate["last"] = now
                    candidate = qr_candidates[seen]
                    if candidate["hits"] >= 3 and now - candidate["first"] >= 4:
                        mode = self.get_mode()
                        if candidate["mode"] != mode:
                            self.on_qr(seen, mode)
                            candidate["mode"] = mode
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                small = cv2.resize(gray, (160, 90))
                if previous is not None:
                    motion_window.append(float(np.mean(cv2.absdiff(small, previous)) / 255.0))
                previous = small
                if now - last_sample >= 15:
                    motion = sum(motion_window) / len(motion_window) if motion_window else None
                    self.on_sample({"motion": motion, "audio": None})
                    motion_window.clear()
                    last_sample = now
            self.camera_status = "off"
        except Exception as exc:
            self.camera_status = "error: " + str(exc)[:100]
        finally:
            if "camera" in locals():
                camera.release()
            if self.stop_event.is_set():
                self.camera_status = "off"

    def _audio_loop(self):
        try:
            import numpy as np
            import sounddevice as sd
            level_sum = 0.0
            level_count = 0
            lock = threading.Lock()

            def callback(indata, frames, timing, status):
                nonlocal level_sum, level_count
                if self.stop_event.is_set():
                    return
                rms = float(np.sqrt(np.mean(np.square(indata, dtype=np.float64))))
                level = min(1.0, rms / 0.12)
                with lock:
                    level_sum += level
                    level_count += 1

            with sd.InputStream(samplerate=16000, channels=1, callback=callback):
                self.audio_status = "on"
                last_sample = time.monotonic()
                while not self.stop_event.wait(0.25):
                    now = time.monotonic()
                    if now - last_sample >= 15:
                        with lock:
                            value = level_sum / level_count if level_count else None
                            level_sum = 0.0
                            level_count = 0
                        self.on_sample({"motion": None, "audio": value})
                        last_sample = now
            self.audio_status = "off"
        except Exception as exc:
            self.audio_status = "unavailable: " + str(exc)[:100]
