# Technical architecture

## Overview

The Multimodal Attendance & Engagement Agent is a local Python web application. The browser dashboard talks only to a Flask service bound to `127.0.0.1`. SQLite stores the roster, attendance times, sessions, and aggregate room signals. Optional camera and microphone workers process data in memory and discard raw frames and samples.

```text
Browser UI (local)
       │ HTTP on loopback
       ▼
Flask routes / JSON API
       ├── SQLite: roster, session times, attendance, room aggregates
       ├── Camera worker: OpenCV QR decode, repeated scan confirmation,
       │                  broad frame difference, low-movement spans
       ├── Audio worker: sounddevice input, transient RMS windows
       ├── Insight agent: explainable context rules and teaching prompts
       └── ML signal model: scikit-learn Isolation Forest, per session
```

## Data flow

1. The educator adds participant names and starts a session. Camera and microphone selection are explicit and off by default.
2. Camera QR scans must repeat over approximately four seconds before the attendance callback records a timestamp. Manual buttons remain available.
3. The camera worker reduces each frame to a small grayscale image and records a broad frame-difference value. It does not save frames or detect faces.
4. The audio worker computes RMS volume from transient input buffers. It does not save or transcribe sound.
5. Modality samples are stored as normalized room-level values with UTC timestamps. The UI plots movement and audio separately.
6. The suggestion agent applies readable rules to recent values and roster status. After at least 13 usable 15-second windows, an Isolation Forest can flag a latest fused window as unusual compared with earlier windows from the active session.
7. The educator reviews attendance and suggestions. Session CSVs and participant summaries are served from the local app.

## Machine-learning method

The optional model uses scikit-learn `IsolationForest` as an unsupervised outlier detector. It uses movement, audio, and their changes between adjacent fused windows, and waits until both sensors have contributed and at least 13 usable windows are available. Intermittent missing values can be filled from a recent value for at most three windows, then by that session’s median. The detector is refitted per session using up to 32 preceding windows and never includes the newest window in its baseline. It reports only whether the room-level signal pattern looks unusual. It is not trained to predict attention or engagement, and it does not label individual learners. Before enough windows exist, rule-based prompts remain available.

## Scenario coverage

| Brief scenario | Implemented behavior | Boundary |
| --- | --- | --- |
| Automated attendance | QR check-in/check-out timestamps after repeated visibility; manual fallback; open check-ins close at session end | QR codes can be shared; educator verifies records |
| Session dynamics | Movement, low-movement span, audio volume, 15-second chart, fused-signal anomaly context | No face/head-pose analysis, speech analysis, or individual engagement score |
| Teaching suggestions | Explainable rules and anomaly context suggest a pause, recap, check-in, or review | Advice only; educator decides and checks with learners |

## Privacy and storage

- No face recognition, face detection, head-pose tracking, identity inference, speech transcription, emotion inference, or individual attention score.
- Frames and microphone buffers are processed transiently and discarded.
- The roster, QR tokens, timestamps, and coarse signal values stay in `instance/classroom.db`.
- Runtime processing makes no cloud or model API requests. Internet is needed to install dependencies or publish the optional demo.
- The default Flask server listens on localhost, not a public network interface.

## System requirements

- **Hardware:** Intel Core i5, 8th generation or later, AMD Ryzen 5, or similar; minimum 8 GB RAM and 16 GB recommended; 256 GB SSD or 500 GB HDD.
- **Operating system:** Windows 10/11, macOS Monterey or later, or Ubuntu 20.04+.
- **Software:** Python 3.8+, Git, and current Chrome, Firefox, or Edge; VS Code is recommended.
- **Network:** stable 10 Mbps internet (20 Mbps recommended) for installing dependencies and deploying the demo. The local application runs without internet after setup.

## Known limitations

This is a supervised-pilot prototype. It does not implement head-pose or face-based tracking because the design avoids face analysis. Movement and volume are coarse room context, not learner engagement measures. Isolation Forest flags statistical novelty rather than educational meaning. QR confirmation can reduce brief false scans, but cannot prevent badge sharing. Sensor access, privacy notice, accessibility, consent, and attendance procedures must be reviewed for the institution before deployment.
