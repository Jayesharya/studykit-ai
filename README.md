# Multimodal Attendance & Engagement Agent

A privacy-first classroom support tool built with Python. It records timestamped attendance, summarizes room-level movement and sound, and offers explainable teaching prompts with an optional offline machine-learning signal check. Educators review every record and decide whether a suggestion fits their classroom.

## Browser demo

The static fictional-data demo is in [`docs/index.html`](docs/index.html) and is [live on GitHub Pages](https://jayesharya.github.io/studykit-ai/). This preview uses fictional names and pre-written sample windows; it does not access a camera or microphone, save entries, or run the Python application or its machine-learning model. The complete local application is available in this repository.

## Project goals

Educational attendance tools often record presence without showing session context. This project brings together voluntary check-in, coarse room-level activity trends, simple session analytics, and human-reviewed teaching ideas. It is designed to run on one computer without sending classroom data to a cloud service.

## Required skills

- Artificial Intelligence
- Machine Learning
- Python

### Scenarios

1. **Automated attendance tracking:** learners present a locally generated QR badge. The camera requires repeated detections over about four seconds before marking attendance, which helps reject brief appearances. Instructors can use manual check-in instead. Check-in and check-out times are recorded; open check-ins are closed at session end.
2. **Session dynamics:** optional camera processing measures broad frame-to-frame movement and low-movement spans. An additional opt-in estimates the room-wide proportion of front-facing versus profile detections. Optional audio processing measures sound level without recording or transcribing speech. The dashboard shows separate 15-second trends; an offline model can flag an unusual combined-signal change.
3. **Teaching suggestions:** visible local rules combine recent room signals and attendance context. A short-term ML anomaly can prompt an educator to check sensor noise or lesson context. Suggestions may propose a check-in, reset, recap, or pacing change, and always leave the decision to the educator.

## Features

- **Python application:** Flask dashboard and API, SQLite records, OpenCV QR/movement and optional coarse head-orientation processing, optional microphone volume analysis, and QR badge generation.
- **Offline machine learning:** scikit-learn Isolation Forest compares the latest fused 15-second room-signal window with earlier windows from that same session. It activates after 13 usable windows when both camera and audio signals are available. It does not use learner identities or a pre-trained attention model.
- **Session analytics:** live roster status, check-in duration, recent sessions, per-participant attendance rate and minutes present, and downloadable session CSVs.
- **Human-reviewed agent:** rule-based teaching prompts plus a room-signal anomaly hint. The software does not issue decisions about learners.
- **Synthetic browser demo:** a no-device, fictional-data preview suitable for trying the screen flow before installing the local app.

## Privacy and limits

The application does not use face recognition, identity inference, persistent face tracking, speech transcription, speaker identification, emotion inference, attention scores, or individual engagement rankings. If the educator explicitly enables coarse head orientation, OpenCV Haar cascades estimate the room-wide front/profile ratio in memory; no face boxes or images are saved. Camera frames are otherwise used for QR decoding and broad frame differences, then discarded. Audio samples are reduced to short-term volume measurements in memory; raw audio is not saved. Names, QR tokens, attendance times, and aggregate room measurements are kept in a local SQLite database in `instance/`.

Movement, front/profile proportions, and volume can reflect the lesson format, room conditions, or sensor placement. They do not measure learning, participation quality, attention, comprehension, or an individual learner’s behavior. QR badges can be shared and sensors can fail. Verify attendance and ask learners directly; do not use this prototype as the sole basis for grading, discipline, or other consequential decisions. Give learners notice and obtain appropriate institutional approval before a pilot.

## Requirements

- **Hardware:** Intel Core i5 (8th generation or later), AMD Ryzen 5, or equivalent; 8 GB RAM minimum and 16 GB recommended; 256 GB SSD or 500 GB HDD. The brief recommends a stable 10 Mbps connection (20 Mbps recommended) for package installation and deployment; runtime processing is local.
- **Software:** Windows 10/11, macOS Monterey or later, or Ubuntu 20.04+; Python 3.8+; Git; and a current Chrome, Firefox, or Edge browser. VS Code or another editor is recommended.
- **Internet:** needed to install dependencies and publish the optional Pages demo. Once packages are installed, classroom data processing makes no network or model API calls.

## Run locally

1. Install Python 3.8 or later.
2. From this project folder, install dependencies: `python -m pip install -r requirements.txt`.
3. Start the app: `python app.py`.
4. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

On Linux, microphone input may need the operating system’s PortAudio package. Camera and microphone are off until selected when starting a session. If a sensor is unavailable, attendance can still be managed manually. Installation needs a network connection; the running application is local.

## Run checks

The API and attendance flow checks use only the Python standard library and Flask:

```bash
python -m pip install "Flask>=3.0,<4"
python -m unittest discover -s tests -v
```

GitHub Actions runs these checks on pushes and pull requests to `main`.

## Use a session

1. Add participants to the local roster.
2. Choose whether to enable the camera and microphone; both are optional.
3. Start a session. For camera check-in, choose check-in mode and hold a participant’s QR badge in view for about four seconds. Switch to check-out mode for a later scan. Manual buttons remain available.
4. Review the roster, session duration, room-level charts, and suggestions. End the session to close any open check-ins.
5. Review participant attendance summaries and download a CSV from Recent Sessions.

## Technical architecture

```text
Local browser dashboard
       │ localhost only
       ▼
Flask application ───────────── SQLite (instance/classroom.db)
       │                            roster, attendance, aggregates
       ├── Camera worker: repeated QR confirmation + frame differences + optional head view
       ├── Audio worker: transient RMS volume windows
       ├── Insight agent: transparent rules + session context
       └── ML signal check: per-session Isolation Forest on fused windows
```

The ML detector needs at least 13 usable windows containing both movement and audio data, uses earlier windows as its baseline, and flags room-signal changes rather than learner states. Short sessions or sessions with only one sensor still receive the explainable rule-based suggestions. There is no generative AI service or remote inference in the runtime.

## Project materials

- [`PROJECT_PLAN.md`](PROJECT_PLAN.md) — implementation map organized as 9 epics and 17 tasks to match the project brief.
- [`docs/TECHNICAL_ARCHITECTURE.md`](docs/TECHNICAL_ARCHITECTURE.md) — components, data flow, system requirements, privacy boundaries, and scenario mapping.
- `app.py` — Flask server, local API, SQLite records, and exports.
- `classroom_agent/monitor.py` — optional QR, movement, and audio workers.
- `classroom_agent/ml_signal_model.py` — offline fused-signal anomaly detector.
- `classroom_agent/agent.py` — explainable teaching suggestions.
- `classroom_agent/templates/` and `classroom_agent/static/` — local dashboard.
- `docs/index.html` — fictional-data GitHub Pages demo.
- `instance/` — local database location, excluded from version control.

## License

MIT. See [LICENSE](LICENSE).
