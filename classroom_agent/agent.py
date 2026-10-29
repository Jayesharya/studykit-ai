from classroom_agent.ml_signal_model import detect_room_activity_anomaly


def build_insights(samples, present_count, roster_count):
    """Return human-reviewed prompts from coarse room-level signals."""
    insights = []
    if not samples:
        insights.append({
            "title": "Gather a few signal windows",
            "body": "Start optional local sensors to see room-level activity trends. No face or voice identities are recognized or tracked.",
            "tone": "neutral",
        })
    else:
        motion_values = [float(row["motion"]) for row in samples if row.get("motion") is not None]
        audio_values = [float(row["audio"]) for row in samples if row.get("audio") is not None]
        recent_motion = sum(motion_values[-4:]) / len(motion_values[-4:]) if motion_values else None
        recent_audio = sum(audio_values[-4:]) / len(audio_values[-4:]) if audio_values else None
        orientation_values = [float(row["orientation"]) for row in samples if row.get("orientation") is not None]
        recent_orientation = sum(orientation_values[-4:]) / len(orientation_values[-4:]) if orientation_values else None
        low_motion_windows = 0
        for value in reversed(motion_values):
            if value >= 0.025:
                break
            low_motion_windows += 1
        if low_motion_windows >= 4:
            minutes = round(low_motion_windows * 15 / 60, 1)
            insights.append({
                "title": "Low room movement for about " + str(minutes) + " minutes",
                "body": "This is a camera-wide movement estimate, not a measure of individual inactivity. A still camera or teaching format can produce the same signal. Check the sensor view and ask the group whether a brief reset would help.",
                "tone": "amber",
            })
        if recent_orientation is not None and recent_orientation < 0.35 and len(orientation_values) >= 3:
            insights.append({
                "title": "Fewer front-facing detections in recent windows",
                "body": "This optional camera-wide front/profile estimate can change with note-taking, group work, or camera placement. It cannot tell who is attentive. Check the room context and ask learners directly before adjusting the session.",
                "tone": "neutral",
            })
        if recent_motion is not None and recent_audio is not None:
            if recent_motion < 0.08 and recent_audio < 0.12 and len(samples) >= 3:
                insights.append({
                    "title": "Try a short reset",
                    "body": "Room movement and sound have both been quiet across recent windows. Consider a verbal check-in, stretch, or quick recall question, then ask learners directly how the pace feels.",
                    "tone": "amber",
                })
            elif recent_audio > 0.55 and recent_motion > 0.35:
                insights.append({
                    "title": "Room activity is elevated",
                    "body": "Both coarse activity signals are high. You could pause for a concise recap or invite one speaker at a time; volume and movement cannot identify participation quality.",
                    "tone": "green",
                })
            else:
                insights.append({
                    "title": "Signals are mixed",
                    "body": "Room-level movement and sound do not point in one direction. Ask learners directly before changing pace.",
                    "tone": "neutral",
                })
        elif recent_audio is not None:
            if recent_audio < 0.10 and len(samples) >= 3:
                body = "The room has been quiet across recent windows. Consider an open question or brief pair discussion, then check with learners."
                tone = "amber"
            else:
                body = "Sound activity is available; it does not reveal who is speaking or whether someone is attentive. Use it as context only."
                tone = "neutral"
            insights.append({"title": "Audio activity context", "body": body, "tone": tone})
        elif recent_motion is not None:
            insights.append({
                "title": "Movement context",
                "body": "Only broad frame-to-frame movement is available. It is not an attention or engagement measurement; ask learners directly for feedback.",
                "tone": "neutral",
            })

    ml_result = detect_room_activity_anomaly(samples)
    if ml_result["ready"] and ml_result["anomaly"]:
        insights.insert(0, {
            "title": "Unusual room-level signal shift",
            "body": "An offline model found this 15-second movement/audio window differs from earlier windows in this session. Check for sensor noise or a change in lesson context, then ask learners directly. This is not an attention score.",
            "tone": "amber",
        })
    elif ml_result["ready"]:
        insights.append({
            "title": "Room signal pattern is within its session baseline",
            "body": "The offline model found no unusual shift in the latest fused window. This does not mean learners are attentive or disengaged; use direct feedback and your classroom context.",
            "tone": "neutral",
        })
    if roster_count and present_count < roster_count:
        insights.append({
            "title": "Attendance check",
            "body": str(present_count) + " of " + str(roster_count) + " rostered participants are currently checked in. Verify the list before ending the session.",
            "tone": "neutral",
        })
    return insights
