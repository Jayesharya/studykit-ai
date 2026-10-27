# StudyKit AI

StudyKit turns a student's notes into a concise summary, active-recall flashcards, and a multiple-choice quiz. It is a standalone learning tool with a server-side Gemini connection and no relationship to an attendance or classroom-monitoring system.

## What it does

- Generates a grounded study kit from notes using Gemini structured JSON output.
- Lets learners flip through recall cards and answer an interactive quiz with explanations.
- Adjusts the explanation level and exports the finished kit as Markdown.
- Keeps the API key on the server. Notes are sent to Gemini only after the learner chooses **Build my study kit**; this app does not store them in a database.

## Run locally

1. Install Node.js 20 or newer.
2. Copy .env.example to .env.
3. Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/app/apikey) and set GEMINI_API_KEY in .env.
4. Run npm start and open http://localhost:3000.

GEMINI_MODEL can be set in .env; the default is gemini-3.8-flash. Never commit .env or put an API key in browser code. For a hosted demo, configure the key as a server-side secret. This app requires a Node server and cannot generate live kits on a static-only host such as GitHub Pages.

## Project notes

This is a newly authored, independent project. It does not copy code from the prior attendance repository. AI assistance was used in creating the project, and the Gemini API powers study-kit generation at runtime. Generated material can contain errors; learners should verify important details against their course materials.

## License

This project is released under the MIT License. See LICENSE.