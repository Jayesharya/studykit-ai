"""Small, offline anomaly detector for aggregate classroom activity signals.

This model is a context-change hint, not an engagement, attention, or learner
classification model. It is fitted independently for each active session.
"""

from datetime import datetime


WINDOW_SECONDS = 15
MIN_WINDOWS = 13


def _fused_windows(samples):
    buckets = {}
    for row in samples:
        stamp = row.get("captured_at")
        if not stamp:
            continue
        try:
            parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
            bucket = int(parsed.timestamp() // WINDOW_SECONDS)
        except (TypeError, ValueError, OverflowError):
            continue
        values = buckets.setdefault(bucket, {"motion": [], "audio": [], "orientation": []})
        for key in ("motion", "audio", "orientation"):
            value = row.get(key)
            if value is not None:
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    continue
                if 0.0 <= number <= 1.0:
                    values[key].append(number)

    windows = []
    for bucket in sorted(buckets):
        values = buckets[bucket]
        if values["motion"] or values["audio"]:
            windows.append({
                "bucket": bucket,
                "motion": sum(values["motion"]) / len(values["motion"]) if values["motion"] else None,
                "audio": sum(values["audio"]) / len(values["audio"]) if values["audio"] else None,
                "orientation": sum(values["orientation"]) / len(values["orientation"]) if values["orientation"] else None,
            })

    # Only call the model multimodal when both optional sensors contributed.
    if not any(window["motion"] is not None for window in windows):
        return []
    if not any(window["audio"] is not None for window in windows):
        return []

    # Carry a recent sensor value for a maximum of three windows. Older gaps
    # remain missing and are filled with the session median below.
    latest = {"motion": None, "audio": None, "orientation": None}
    for window in windows:
        for key in latest:
            if window[key] is not None:
                latest[key] = (window[key], window["bucket"])
            elif latest[key] is not None and window["bucket"] - latest[key][1] <= 3:
                window[key] = latest[key][0]

    usable = [w for w in windows if w["motion"] is not None or w["audio"] is not None]
    for key in ("motion", "audio", "orientation"):
        values = [w[key] for w in usable if w[key] is not None]
        fill = sorted(values)[len(values) // 2] if values else 0.0
        for window in usable:
            if window[key] is None:
                window[key] = fill

    return usable


def detect_room_activity_anomaly(samples):
    """Flag a latest fused window that differs from prior windows in-session."""
    windows = _fused_windows(samples)
    if len(windows) < MIN_WINDOWS:
        return {"ready": False, "anomaly": False, "windows": len(windows)}

    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return {"ready": False, "anomaly": False, "windows": len(windows)}

    features = []
    previous = None
    for window in windows:
        motion = window["motion"]
        audio = window["audio"]
        orientation = window["orientation"]
        motion_delta = 0.0 if previous is None else motion - previous[0]
        audio_delta = 0.0 if previous is None else audio - previous[1]
        orientation_delta = 0.0 if previous is None else orientation - previous[2]
        features.append([motion, audio, orientation, motion_delta, audio_delta, orientation_delta])
        previous = (motion, audio, orientation)

    # Keep a bounded baseline. Never fit on the current observation.
    baseline = features[-33:-1]
    if len(baseline) < MIN_WINDOWS - 1:
        return {"ready": False, "anomaly": False, "windows": len(windows)}

    model = IsolationForest(
        n_estimators=100,
        contamination="auto",
        random_state=17,
    )
    model.fit(baseline)
    anomaly = bool(model.predict([features[-1]])[0] == -1)
    return {"ready": True, "anomaly": anomaly, "windows": len(windows)}
