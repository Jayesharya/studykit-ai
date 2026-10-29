const $ = (selector) => document.querySelector(selector);
let state = null;
let toastTimer = null;

async function api(path, options) {
  const response = await fetch(path, options || {});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || "The local request did not complete.");
  return body;
}

function notify(message) {
  const box = $("#toast");
  box.textContent = message;
  box.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => box.classList.remove("show"), 2500);
}

function clock(value) {
  return value ? new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";
}

function elapsed(start) {
  if (!start) return "00:00";
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(start)) / 1000));
  return String(Math.floor(seconds / 60)).padStart(2, "0") + ":" + String(seconds % 60).padStart(2, "0");
}

function renderRoster() {
  const roster = state?.roster || [];
  const session = state?.session;
  const records = new Map((session?.attendance || []).map((row) => [row.student_id, row]));
  $("#rosterCount").textContent = String(roster.length).padStart(2, "0");
  const list = $("#rosterList");
  list.replaceChildren();
  if (!roster.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Add participants above.";
    list.append(empty);
    return;
  }
  roster.forEach((person) => {
    const record = records.get(person.id);
    const present = Boolean(record && !record.check_out);
    const row = document.createElement("div");
    row.className = "person";
    const dot = document.createElement("i");
    dot.className = "dot " + (present ? "present" : "absent");
    const meta = document.createElement("div");
    const name = document.createElement("b");
    const id = document.createElement("small");
    name.textContent = person.name;
    const minutes = record ? Math.max(0, Math.floor((new Date(record.check_out || Date.now()) - new Date(record.check_in)) / 60000)) : 0;
    id.textContent = person.id + (record ? " · " + (record.check_out ? "out " + clock(record.check_out) : "in " + clock(record.check_in)) + " · " + minutes + "m" : "");
    meta.append(name, id);
    const action = document.createElement("button");
    action.className = "action";
    action.textContent = present ? "Check out" : "Check in";
    action.disabled = !session;
    action.onclick = () => attendance(person.id, present ? "out" : "in");
    const qr = document.createElement("button");
    qr.className = "action";
    qr.textContent = "QR";
    qr.title = "Show private local badge";
    qr.onclick = () => showQr(person);
    row.append(dot, meta, action, qr);
    list.append(row);
  });
}

function renderHistory() {
  const list = $("#historyList");
  list.replaceChildren();
  const rows = (state?.history || []).filter((item) => item.ended_at).slice(0, 5);
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Completed sessions appear here.";
    list.append(empty);
    return;
  }
  rows.forEach((item) => {
    const row = document.createElement("div");
    row.className = "history-row";
    const title = document.createElement("b");
    const date = document.createElement("small");
    const link = document.createElement("a");
    title.textContent = item.title;
    date.textContent = new Date(item.started_at).toLocaleDateString() + " · " + clock(item.started_at);
    link.href = "/api/sessions/" + encodeURIComponent(item.id) + "/export.csv";
    link.textContent = "CSV ↓";
    row.append(title, date, link);
    list.append(row);
  });
}

function renderAnalytics() {
  const data = state?.analytics || {};
  const total = Number(data.session_count || 0);
  $("#analyticsSessionCount").textContent = String(total).padStart(2, "0") + " SESSIONS";
  const list = $("#analyticsList");
  list.replaceChildren();
  const people = data.participants || [];
  if (!people.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Add participants and complete sessions to build a history.";
    list.append(empty);
    return;
  }
  people.forEach((person) => {
    const row = document.createElement("div");
    row.className = "analytics-row";
    const name = document.createElement("b");
    const details = document.createElement("small");
    const rate = document.createElement("strong");
    name.textContent = person.name;
    details.textContent = person.sessions_attended + " / " + person.sessions_total + " sessions · " + person.minutes_present + " min present";
    rate.textContent = Number(person.attendance_rate).toFixed(0) + "%";
    row.append(name, details, rate);
    list.append(row);
  });
}

function drawChart(samples) {
  const canvas = $("#activityChart");
  const context = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  context.scale(ratio, ratio);
  const width = rect.width;
  const height = rect.height;
  const padding = 12;
  context.clearRect(0, 0, width, height);
  const motion = samples.map((row) => row.motion == null ? null : Number(row.motion));
  const audio = samples.map((row) => row.audio == null ? null : Number(row.audio));
  const orientation = samples.map((row) => row.orientation == null ? null : Number(row.orientation));
  const hasSignals = motion.some((value) => value !== null) || audio.some((value) => value !== null) || orientation.some((value) => value !== null);
  $("#chartEmpty").hidden = hasSignals;
  if (!hasSignals) return;
  function line(values, color) {
    const points = values.map((value, index) => ({ value, index })).filter((point) => point.value !== null);
    if (!points.length) return;
    context.beginPath();
    points.forEach((point, index) => {
      const x = padding + (points.length < 2 ? 0 : point.index / Math.max(1, values.length - 1) * (width - padding * 2));
      const y = height - padding - Math.max(0, Math.min(1, point.value)) * (height - padding * 2);
      if (index) context.lineTo(x, y); else context.moveTo(x, y);
    });
    context.strokeStyle = color;
    context.lineWidth = 2;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.stroke();
  }
  line(motion, "#286c50");
  line(audio, "#f08d69");
  line(orientation, "#7c6bc4");
}

function renderInsights(items) {
  const list = $("#insightsList");
  list.replaceChildren();
  (items || []).forEach((item) => {
    const card = document.createElement("div");
    const icon = document.createElement("i");
    const copy = document.createElement("div");
    const title = document.createElement("b");
    const body = document.createElement("p");
    card.className = "insight" + (item.tone === "amber" ? " amber" : "");
    icon.textContent = item.tone === "amber" ? "↘" : "✳";
    title.textContent = item.title;
    body.textContent = item.body;
    copy.append(title, body);
    card.append(icon, copy);
    list.append(card);
  });
}

function render() {
  if (!state) return;
  const session = state.session;
  const devices = state.devices || {};
  const camera = devices.camera === "on";
  const audio = devices.audio === "on";
  const orientation = devices.head_pose === "on";
  $("#sessionState").textContent = session ? "SESSION LIVE" : "NOT STARTED";
  $("#sessionState").classList.toggle("active", Boolean(session));
  $("#startSession").disabled = Boolean(session);
  $("#endSession").disabled = !session;
  $("#sessionTitle").disabled = Boolean(session);
  $("#cameraToggle").disabled = Boolean(session);
  $("#orientationToggle").disabled = Boolean(session);
  $("#audioToggle").disabled = Boolean(session);
  $("#overviewTitle").textContent = session ? session.title : "Ready when you are.";
  $("#liveStatus").textContent = session ? "SESSION LIVE" : "READY";
  $("#liveChip").classList.toggle("on", Boolean(session));
  $("#presentMetric").textContent = session ? String(session.present_count).padStart(2, "0") : "—";
  $("#presentDetail").textContent = session ? "of " + session.roster_count + " rostered" : "Start a session";
  $("#durationMetric").textContent = session ? elapsed(session.started_at) : "00:00";
  $("#startedDetail").textContent = session ? "Started " + clock(session.started_at) : "Waiting to start";
  $("#deviceMetric").textContent = session ? (Number(camera) + Number(audio) + Number(orientation)) + " / 3" : "—";
  $("#deviceDetail").textContent = session ? "camera " + devices.camera + " · mic " + devices.audio + " · head view " + devices.head_pose : "Optional and local";
  if (session) {
    $("#sessionTitle").value = session.title;
    $("#cameraToggle").checked = Boolean(session.camera_enabled);
    $("#audioToggle").checked = Boolean(session.audio_enabled);
    $("#orientationToggle").checked = Boolean(session.orientation_enabled);
  }
  $("#modeIn").setAttribute("aria-pressed", String((devices.scanner_mode || "in") === "in"));
  $("#modeOut").setAttribute("aria-pressed", String((devices.scanner_mode || "in") === "out"));
  $("#modeIn").disabled = !session || !session.camera_enabled;
  $("#modeOut").disabled = !session || !session.camera_enabled;
  renderRoster();
  renderHistory();
  renderAnalytics();
  drawChart(session?.samples || []);
  renderInsights(session?.insights || []);
}

async function refresh() {
  try {
    state = await api("/api/state");
    render();
  } catch (error) {
    $("#liveStatus").textContent = "LOCAL SERVER UNAVAILABLE";
  }
}

async function attendance(studentId, mode) {
  try {
    const result = await api("/api/attendance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId, mode }),
    });
    notify(result.message);
    await refresh();
  } catch (error) { notify(error.message); }
}

function showQr(person) {
  $("#qrName").textContent = person.name + " · " + person.id;
  $("#qrImage").src = "/api/roster/" + encodeURIComponent(person.id) + "/qr?t=" + Date.now();
  $("#qrDialog").showModal();
}

async function setScannerMode(mode) {
  try {
    await api("/api/sessions/mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    notify(mode === "in" ? "QR scanner set to check-in." : "QR scanner set to check-out.");
    await refresh();
  } catch (error) { notify(error.message); }
}

$("#modeIn").addEventListener("click", () => setScannerMode("in"));
$("#modeOut").addEventListener("click", () => setScannerMode("out"));
$("#startSession").addEventListener("click", async () => {
  const box = $("#errorMessage");
  box.hidden = true;
  try {
    await api("/api/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: $("#sessionTitle").value, camera: $("#cameraToggle").checked, orientation: $("#orientationToggle").checked, audio: $("#audioToggle").checked }),
    });
    notify("Local session started.");
    await refresh();
  } catch (error) { box.textContent = error.message; box.hidden = false; }
});
$("#endSession").addEventListener("click", async () => {
  const box = $("#errorMessage");
  box.hidden = true;
  try {
    await api("/api/sessions/end", { method: "POST" });
    notify("Session saved locally; open check-ins closed.");
    await refresh();
  } catch (error) { box.textContent = error.message; box.hidden = false; }
});
$("#addParticipant").addEventListener("click", async () => {
  try {
    await api("/api/roster", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: $("#participantName").value, id: $("#participantId").value }),
    });
    $("#participantName").value = "";
    $("#participantId").value = "";
    notify("Added to the local roster.");
    await refresh();
  } catch (error) { notify(error.message); }
});
$("#participantName").addEventListener("keydown", (event) => { if (event.key === "Enter") $("#addParticipant").click(); });
$("#privacyButton").onclick = () => $("#privacyDialog").showModal();
$("#footerPrivacy").onclick = () => $("#privacyDialog").showModal();
$("#closePrivacy").onclick = () => $("#privacyDialog").close();
$("#donePrivacy").onclick = () => $("#privacyDialog").close();
$("#closeQr").onclick = () => $("#qrDialog").close();
window.addEventListener("resize", () => state && drawChart(state.session?.samples || []));
refresh();
setInterval(() => {
  refresh();
  if (state?.session) $("#durationMetric").textContent = elapsed(state.session.started_at);
}, 5000);
