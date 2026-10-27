import { createServer } from "node:http";
import { readFile, access } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("./", import.meta.url));
const publicDir = join(root, "public");
try {
  const envFile = await readFile(join(root, ".env"), "utf8");
  for (const line of envFile.split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (match && !process.env[match[1]]) process.env[match[1]] = match[2].replace(/^(['"])(.*)\1$/, "$2");
  }
} catch {}

const model = process.env.GEMINI_MODEL || "gemini-3.8-flash";
const maxNoteLength = 18000;
const outputSchema = {
  type: "object",
  properties: {
    title: { type: "string" },
    summary: { type: "string" },
    keyIdeas: { type: "array", items: { type: "string" } },
    flashcards: { type: "array", items: { type: "object", properties: { question: { type: "string" }, answer: { type: "string" } }, required: ["question", "answer"] } },
    quiz: { type: "array", items: { type: "object", properties: { question: { type: "string" }, choices: { type: "array", items: { type: "string" } }, answerIndex: { type: "integer" }, explanation: { type: "string" } }, required: ["question", "choices", "answerIndex", "explanation"] },
    nextSteps: { type: "array", items: { type: "string" } }
  },
  required: ["title", "summary", "keyIdeas", "flashcards", "quiz", "nextSteps"]
};
const mimeTypes = { ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8" };

function sendJson(response, status, value) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
  response.end(JSON.stringify(value));
}
async function readRequestBody(request) {
  let body = "";
  for await (const chunk of request) {
    body += chunk;
    if (body.length > maxNoteLength + 2000) throw new Error("request_too_large");
  }
  return JSON.parse(body || "{}");
}
async function generateKit(request, response) {
  if (!process.env.GEMINI_API_KEY) return sendJson(response, 503, { error: "Add GEMINI_API_KEY to your local .env file to generate a study kit." });
  let payload;
  try { payload = await readRequestBody(request); }
  catch (error) {
    const tooLarge = error.message === "request_too_large";
    return sendJson(response, tooLarge ? 413 : 400, { error: tooLarge ? "These notes are too long. Please keep them under 18,000 characters." : "The request could not be read. Please try again." });
  }
  const notes = typeof payload.notes === "string" ? payload.notes.trim() : "";
  const level = typeof payload.level === "string" ? payload.level.slice(0, 40) : "Clear and concise";
  if (notes.length < 40) return sendJson(response, 400, { error: "Paste at least a few sentences of notes first." });
  if (notes.length > maxNoteLength) return sendJson(response, 413, { error: "These notes are too long. Please keep them under 18,000 characters." });

  const prompt = "Turn the student's notes into a useful, accurate study kit. Use only facts supported by the notes. If a detail is unclear, say so rather than inventing it. Write at a " + level + " level. Make 5 to 8 flashcards and 4 multiple-choice questions, each with 4 choices. Keep explanations short. Return the requested JSON fields only.\n\nSTUDENT NOTES:\n" + notes;
  try {
    const apiResponse = await fetch("https://generativelanguage.googleapis.com/v1beta/interactions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": process.env.GEMINI_API_KEY },
      body: JSON.stringify({ model, input: prompt, response_format: { type: "text", mime_type: "application/json", schema: outputSchema } }),
      signal: AbortSignal.timeout(60000)
    });
    const result = await apiResponse.json().catch(() => ({}));
    if (!apiResponse.ok) return sendJson(response, apiResponse.status === 429 ? 429 : 502, { error: apiResponse.status === 429 ? "The AI service is busy right now. Please try again in a moment." : "The AI request did not complete. Check the server key and try again." });
    const outputText = result.output_text || (result.output && result.output.find((item) => item.type === "text")?.text);
    if (!outputText) return sendJson(response, 502, { error: "The AI returned an empty study kit. Please try again." });
    return sendJson(response, 200, { kit: JSON.parse(outputText), model });
  } catch (error) {
    const timeout = error.name === "TimeoutError";
    return sendJson(response, timeout ? 504 : 502, { error: timeout ? "The AI request took too long. Please try again." : "The response could not be prepared. Please try again." });
  }
}

const server = createServer(async (request, response) => {
  response.setHeader("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
  response.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
  response.setHeader("X-Content-Type-Options", "nosniff");
  const url = new URL(request.url, "http://localhost");
  if (request.method === "POST" && url.pathname === "/api/generate") return generateKit(request, response);
  if (request.method !== "GET" && request.method !== "HEAD") return response.writeHead(405, { Allow: "GET, HEAD, POST" }).end();
  let requestedPath;
  try { requestedPath = url.pathname === "/" ? "/index.html" : decodeURIComponent(url.pathname); }
  catch { return response.writeHead(400).end(); }
  const base = resolve(publicDir);
  const filePath = resolve(publicDir, "." + normalize(requestedPath));
  if (filePath !== base && !filePath.startsWith(base + "/") && !filePath.startsWith(base + "\\")) return response.writeHead(403).end();
  try {
    await access(filePath);
    const data = await readFile(filePath);
    response.writeHead(200, { "Content-Type": mimeTypes[extname(filePath)] || "application/octet-stream", "Cache-Control": "no-cache" });
    response.end(request.method === "HEAD" ? undefined : data);
  } catch { response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }).end("Not found"); }
});
const port = Number(process.env.PORT) || 3000;
server.listen(port, "0.0.0.0", () => console.log("StudyKit is ready at http://localhost:" + port));