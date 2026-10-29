# Implementation map

This project map organizes the brief’s scope into **9 epics and 17 tasks**. It is an implementation checklist for this repository; the project listing does not provide the original task titles. There is no mentor assigned in the brief.

## Epic 1 — Session management

- [x] Create and end a local classroom session.
- [x] Store session title, timestamps, and optional sensor settings.

## Epic 2 — Participant roster and identity choice

- [x] Maintain a local participant roster and generate private QR tokens.
- [x] Provide manual attendance as a sensor-independent option.

## Epic 3 — Sustained attendance confirmation

- [x] Require repeated QR observations over about four seconds before camera check-in.
- [x] Record check-in/check-out times and close open records when a session ends.

## Epic 4 — Computer-vision room signals

- [x] Decode QR badges and measure broad frame-to-frame room movement with OpenCV.
- [x] Summarize consecutive low-movement windows without identifying or tracking individuals.

## Epic 5 — Audio room signals

- [x] Compute short-window audio volume locally without saving raw sound.
- [x] Show audio activity independently from camera movement.

## Epic 6 — Multimodal machine-learning context

- [x] Fuse available movement and audio features into 15-second windows.
- [x] Use a per-session Isolation Forest to flag unusual room-signal shifts after a baseline forms.

## Epic 7 — Teaching suggestion agent

- [x] Use readable local rules for quiet, elevated, mixed, and attendance contexts.
- [x] Present optional suggestions and ML flags for educator review.

## Epic 8 — Session and participant analytics

- [x] Summarize attendance count, check-in duration, and recent sessions.
- [x] Show each participant’s session attendance rate and total minutes present; export session CSV.

## Epic 9 — Privacy, offline operation, and submission materials

- [x] Keep runtime records on the local device and document privacy limits.
- [x] Provide setup instructions, system requirements, architecture notes, and a fictional-data web demo.
