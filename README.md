# Multimodal Attendance & Engagement Agent

A local-first classroom assistant for timestamped QR attendance, coarse room-activity trends, and explainable teaching prompts. The dashboard is a decision-support aid: educators verify attendance and decide whether a suggestion fits.

## Browser demo

[Open the interactive demo](https://jayesharya.github.io/studykit-ai/). The public page is an illustrative simulation using fictional data. It does not request camera or microphone access and does not contain a live attendance service.

## What it does

- **Automated attendance:** locally generated participant QR badges support check-in and check-out timestamps. Session duration is available in the local export.
- **Room dynamics:** optional OpenCV camera processing scans QR codes and measures broad frame-to-frame movement. Optional audio processing measures volume levels in short windows.
- **Local insight agent:** transparent, rule-based prompts use coarse room signals and attendance counts to suggest a check-in, pause, recap, or pacing change.
- **Session analytics:** view attendance and room-level signal trends, review recent sessions, and export attendance as CSV.
- **Offline by design:** after dependencies are installed, runtime processing and records stay on the host computer. The application makes no cloud or model API calls.

## Privacy boundaries

This implementation deliberately avoids face recognition, identity inference from video, speech transcription, emotion detection, individual attention scores, and individual engagement rankings. A QR badge identifies a participant only when they choose to present it. Video frames and audio samples are processed transiently in memory and are not saved. Only check-in timestamps and coarse movement/audio levels are stored in a local SQLite database under \`instance/\`.

The public browser demo is simulated. Do not use this prototype as the sole source for attendance, grading, discipline, or other consequential decisions. Obtain appropriate institutional approval and learner notice before classroom use.

## Run locally

**Requirements:** Python 3.8+, Windows 10/11, macOS Monterey or later, or Ubuntu 20.04+. A modern Chrome, Firefox, or Edge browser is recommended. An Intel Core i5 (8th generation+) or equivalent Ryzen 5, 8 GB RAM minimum (16 GB recommended), and 256 GB SSD are suitable for a small pilot.

1. Install Python 3.8 or later.
2. In this directory, install the packages with \`python -m pip install -r requirements.txt\`.
3. Start the dashboard with \`python app.py\`.
4. Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

The first package installation needs network access. Once installed, the application itself can run offline. On Linux, audio capture may require the operating system's PortAudio library. If a camera or microphone is unavailable, attendance can still be recorded manually and the app reports the sensor status.

## Use a session

1. Add participants to the local roster. The public browser demo uses fictional sample data.
2. Choose whether to enable the camera and/or microphone. Both are off until explicitly selected.
3. Start a session. Use each participant's **QR** button to display their locally generated badge. Use the dashboard's QR Scanner Mode buttons to choose check-in or check-out, or use the manual buttons.
4. Review current check-ins, session duration, and the separate room-signal trends. End the session to close open check-ins.
5. Download a CSV from Recent Sessions.

A QR scan records a check-in only once per session. A later check-out is recorded when the instructor switches to the check-out flow; an open check-in is closed when the session ends. The browser demo illustrates this flow with fictional values.

## Technical architecture

\`\`\`text
Local browser dashboard
        │ localhost only
        ▼
Flask routes ─────────────── SQLite (instance/classroom.db)
        │                         roster, timestamps, aggregates
        ├── Camera worker: QR decode + coarse frame difference
        ├── Audio worker: transient RMS volume windows
        └── Local insight agent: transparent rules → teaching prompts
\`\`\`

The camera and microphone workers never persist raw frames, images, waveforms, or speech. The insight agent is a small offline decision-support component, not a trained attention or emotion classifier. AI assistance was used while developing this prototype; runtime suggestions follow fixed local rules.

## Requirements and planning snapshot

- Skills: Artificial Intelligence, Machine Learning, Python.
- Hardware: Intel Core i5 (8th generation+) / AMD Ryzen 5 equivalent; 8 GB RAM minimum, 16 GB recommended; 256 GB SSD (or 500 GB HDD).
- Software: Python 3.8+, Git, VS Code or another editor, and a current Chrome/Firefox/Edge browser.
- The project brief lists 9 epics and 17 tasks; no mentor is currently assigned.

## Project layout

- \`app.py\` — local Flask server and attendance/session API.
- \`classroom_agent/monitor.py\` — optional QR/motion and audio workers.
- \`classroom_agent/agent.py\` — explainable local suggestion rules.
- \`classroom_agent/templates/\` and \`static/\` — local dashboard UI.
- \`docs/\` — static GitHub Pages demonstration with synthetic data.
- \`instance/\` — local database; excluded from version control.

## Limitations

This is a prototype for supervised pilots. QR badges can be shared, room movement is a coarse visual signal, and volume level cannot identify a speaker or determine participation quality. The demo's sample values are fictional. The signal agent is rule-based and does not claim to measure learning or attention.

## License

MIT. See [LICENSE](LICENSE).