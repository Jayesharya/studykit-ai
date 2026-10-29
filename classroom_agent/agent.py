def build_insights(samples, present_count, roster_count):
    """Return explainable prompts from coarse room-level signals, never attention scores."""
    insights = []
    if not samples:
        insights.append({
            "title": "Gather a few signal windows",
            "body": "Start an optional camera or microphone stream to see room-level activity trends. No face or voice identity analysis is performed.",
            "tone": "neutral",
        })
    else:
        motion_values = [float(row["motion"]) for row in samples if row.get("motion") is not None]
        audio_values = [float(row["audio"]) for row in samples if row.get("audio") is not None]
        recent_motion = sum(motion_values[-4:]) / len(motion_values[-4:]) if motion_values else None
        recent_audio = sum(audio_values[-4:]) / len(audio_values[-4:]) if audio_values else None
        if recent_motion is not None and recent_audio is not None:
            if recent_motion < 0.08 and recent_audio < 0.12 and len(samples) >= 3:
                insights.append({
                    "title": "Try a short reset",
                    "body": "Room movement and sound have both been quiet across recent windows. Consider a verbal check-in, stretch, or quick recall question.",
                    "tone": "amber",
                })
            elif recent_audio > 0.55 and recent_motion > 0.35:
                insights.append({
                    "title": "Room activity is elevated",
                    "body": "Both coarse activity signals are high. You could pause for a concise recap or invite one speaker at a time.",
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
    if roster_count and present_count < roster_count:
        insights.append({
            "title": "Attendance check",
            "body": str(present_count) + " of " + str(roster_count) + " rostered participants are currently checked in. Verify the list before ending the session.",
            "tone": "neutral",
        })
    return insights