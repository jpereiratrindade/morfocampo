/**
 * app.js — morfocampo web SPA
 *
 * Fluxo:
 *   Tela 1 (home)    → lista campanhas / cria campanha
 *   Tela 2 (session) → seleciona parcela + observador → abre sessão de coleta
 *   Tela 3 (collect) → grava áudio / digita fala → interpreta → confirma → salva
 *   Tela 4 (records) → lista registros DO observador atual + corrigir + deletar
 *   Tela 5 (validate)→ valida campanha + baixa exportação
 */

// ─── Estado global ────────────────────────────────────────────────────────────

const State = {
  campaigns: [],
  currentCampaign: null,   // { id, project_id, campaign_id, area, ... }
  session: {
    observer: "",
    plot: "",
    date: new Date().toISOString().slice(0, 10),
  },
  parsedRecord: null,       // último registro interpretado pelo C++
  audioBlob: null,          // blob do áudio gravado
  audioFilename: null,      // nome salvo no servidor
  records: [],              // registros DO observador atual
  isRecording: false,
  mediaRecorder: null,
  speechRecognition: null,
  currentTranscript: "",
  activeTab: "collect",     // "collect" | "records" | "validate"
};

// ─── Utilitários DOM ──────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);
const show = id => { $(id).classList.add("active"); };
const hide = id => { $(id).classList.remove("active"); };

function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  const el = document.querySelector(`.screen[data-screen="${name}"]`);
  if (el) el.classList.add("active");
}

function toast(msg, type = "success", duration = 3000) {
  const container = $("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

function renderMarkdown(md) {
  // Conversão mínima de Markdown para HTML (sem dependência externa)
  return md
    .replace(/^#### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/gs, m => `<ul>${m}</ul>`)
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br>")
    .replace(/^(?!<[hup])/gm, "");
}

// ─── API helpers ──────────────────────────────────────────────────────────────

async function api(method, path, body = null, isForm = false) {
  const opts = { method, headers: {} };
  if (body && !isForm) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  } else if (body && isForm) {
    opts.body = body; // FormData
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ─── Tela HOME & Identificação do Observador ──────────────────────────────────

function loadGlobalObserver() {
  const obs = localStorage.getItem("morfocampo_global_observer");
  if (obs) {
    State.session.observer = obs;
    $("home-user-btn").innerHTML = `👤 ${obs}`;
    $("home-user-btn").style.background = "rgba(34,197,94,0.15)";
    $("home-user-btn").style.color = "var(--green)";
    $("home-user-btn").style.borderColor = "var(--green-dim)";
    $("global-observer").value = obs;
  }
}

function toggleUserPanel() {
  const panel = $("user-panel");
  if (panel.style.display === "none" || !panel.style.display) {
    panel.style.display = "block";
    $("global-observer").focus();
  } else {
    panel.style.display = "none";
  }
}

function saveObserver() {
  const obs = $("global-observer").value.trim();
  if (obs) {
    localStorage.setItem("morfocampo_global_observer", obs);
    State.session.observer = obs;
    toast(`Observador definido: ${obs}`);
  } else {
    localStorage.removeItem("morfocampo_global_observer");
    State.session.observer = "";
    $("home-user-btn").innerHTML = `👤 —`;
    $("home-user-btn").style.background = "rgba(239,68,68,0.15)";
    $("home-user-btn").style.color = "var(--red)";
    $("home-user-btn").style.borderColor = "var(--red-dim)";
    toast("Identificação removida", "warn");
  }
  loadGlobalObserver();
  $("user-panel").style.display = "none";
}

async function loadCampaigns() {
  try {
    const campaigns = await api("GET", "/api/campaigns");
    State.campaigns = campaigns;
    renderCampaignList(campaigns);
  } catch (e) {
    toast("Erro ao carregar campanhas: " + e.message, "error");
  }
}

function renderCampaignList(campaigns) {
  const list = $("campaign-list");
  if (!campaigns.length) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="icon">🌿</div>
        <p>Nenhuma campanha ainda.<br>Crie uma para começar.</p>
      </div>`;
    return;
  }
  list.innerHTML = campaigns.map(c => `
    <div class="record-item ok" style="margin-bottom:10px">
      <div class="record-id">${c.campaign_id}</div>
      <div class="record-info" style="cursor:pointer" onclick="selectCampaign(${c.id})">
        <div class="record-main">${c.project_id}</div>
        <div class="record-sub">${c.area || "—"} &nbsp;·&nbsp; ${c.record_count} registros</div>
      </div>
      <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end">
        <button class="btn btn-primary btn-sm" onclick="selectCampaign(${c.id})">🎙 Coletar</button>
        <button class="btn btn-ghost btn-sm" onclick="openAdmin(${c.id})" style="color:var(--blue);border-color:var(--blue)">⚙ Admin</button>
      </div>
    </div>`).join("");
}

async function createCampaign() {
  const project  = $("new-project").value.trim();
  const campaign = $("new-campaign").value.trim();
  const area     = $("new-area").value.trim();
  const maxCap   = parseFloat($("new-max-cap").value) || null;
  const maxDap   = parseFloat($("new-max-dap").value) || null;
  const maxH     = parseFloat($("new-max-height").value) || null;

  if (!project || !campaign) {
    toast("Projeto e campanha são obrigatórios", "warn"); return;
  }
  try {
    await api("POST", "/api/campaigns", {
      project_id: project, campaign_id: campaign, area,
      max_cap_cm: maxCap, max_dap_cm: maxDap, max_height_m: maxH,
    });
    toast("Campanha criada!");
    $("create-form").classList.add("hidden");
    clearCreateForm();
    await loadCampaigns();
  } catch (e) {
    toast("Erro: " + e.message, "error");
  }
}

function clearCreateForm() {
  ["new-project","new-campaign","new-area",
   "new-max-cap","new-max-dap","new-max-height"].forEach(id => { $(id).value = ""; });
}

function toggleCreateForm() {
  $("create-form").classList.toggle("hidden");
}

// ─── Tela ADMIN ───────────────────────────────────────────────────────────────

async function openAdmin(campaignId) {
  showScreen("admin");
  $("admin-campaign-info").innerHTML = `<div class="loading-spinner" style="margin:auto"></div>`;
  $("admin-stats").innerHTML = "";
  $("admin-by-observer").innerHTML = "";
  $("admin-report").innerHTML = "";
  $("admin-last-validation").innerHTML = "";

  try {
    const data = await api("GET", `/api/campaigns/${campaignId}/admin/summary`);
    State.currentCampaign = data.campaign;  // usado por adminValidate/adminExport

    // Info da campanha
    const c = data.campaign;
    $("admin-title").textContent = `${c.project_id} / ${c.campaign_id}`;
    const limits = [
      c.max_cap_cm  ? `CAP ≤ ${c.max_cap_cm} cm`  : null,
      c.max_dap_cm  ? `DAP ≤ ${c.max_dap_cm} cm`  : null,
      c.max_height_m? `Alt ≤ ${c.max_height_m} m`  : null,
    ].filter(Boolean).join(" · ") || "Sem limites configurados";

    $("admin-campaign-info").innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div>
          <div style="font-size:1.1rem;font-weight:700;color:var(--text-hi)">${c.project_id}</div>
          <div style="color:var(--text-dim);font-size:0.9rem;margin-top:2px">${c.area || "Área não definida"}</div>
          <div style="font-size:0.75rem;color:var(--text-muted);margin-top:6px">${limits}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:2rem;font-weight:700;color:var(--blue);font-family:var(--font-mono)">${data.total_records}</div>
          <div style="font-size:0.7rem;color:var(--text-muted);text-transform:uppercase">registros totais</div>
        </div>
      </div>`;

    // Stats de flags
    const f = data.flag_counts;
    $("admin-stats").innerHTML = `
      <div class="stats-row">
        <div class="stat-box"><div class="stat-num green">${f.ok || 0}</div><div class="stat-label">OK</div></div>
        <div class="stat-box"><div class="stat-num amber">${f.revisar || 0}</div><div class="stat-label">Revisar</div></div>
        <div class="stat-box"><div class="stat-num blue">${f.incompleto || 0}</div><div class="stat-label">Incompl.</div></div>
        <div class="stat-box"><div class="stat-num red">${f.erro || 0}</div><div class="stat-label">Erro</div></div>
      </div>`;

    // Última validação
    if (data.last_validation) {
      const v = data.last_validation;
      $("admin-last-validation").innerHTML = `
        <div class="card" style="border-color:var(--border-hi);font-size:0.85rem">
          <div class="card-title" style="margin-bottom:6px">Última validação — ${v.run_at}</div>
          <div style="display:flex;gap:16px;color:var(--text-dim)">
            <span><span style="color:var(--red);font-weight:700">${v.error_count}</span> erros</span>
            <span><span style="color:var(--amber);font-weight:700">${v.warning_count}</span> avisos</span>
            <span><span style="color:var(--blue);font-weight:700">${v.total_records}</span> registros</span>
          </div>
        </div>`;
    }

    // Por observador
    const obsEntries = Object.entries(data.by_observer);
    if (!obsEntries.length) {
      $("admin-by-observer").innerHTML = `
        <div class="empty-state"><div class="icon">📋</div>
        <p>Nenhum registro ainda nesta campanha.</p></div>`;
      return;
    }

    $("admin-by-observer").innerHTML = `<h3 style="color:var(--text-hi)">Registros por observador</h3>`;

    for (const [obs, { count, records }] of obsEntries) {
      const obsCard = document.createElement("details");
      obsCard.open = obsEntries.length === 1;
      obsCard.style.cssText = "background:var(--card);border:1px solid var(--border);border-radius:var(--radius-sm);margin-top:10px";
      obsCard.innerHTML = `
        <summary style="padding:12px 14px;cursor:pointer;user-select:none;display:flex;align-items:center;gap:10px;list-style:none">
          <span style="font-weight:700;color:var(--text-hi);flex:1">${obs}</span>
          <span class="confidence-badge ok" style="font-size:0.75rem">${count} registros</span>
        </summary>
        <div style="padding:0 10px 10px">
          ${records.map(r => {
            const flag = r.confidence_flag || "ok";
            const cap = r.cap_cm ? `CAP ${r.cap_cm.toFixed(1)}` : "";
            const dap = r.dap_cm ? `DAP ${r.dap_cm.toFixed(1)}` : "";
            return `
              <div class="record-item ${flag === 'erro' ? 'has-error' : flag !== 'ok' ? 'has-warn' : 'ok'}" style="margin-bottom:6px">
                <div class="record-id">${r.tree_id || "—"}</div>
                <div class="record-info">
                  <div class="record-main">${[cap,dap].filter(Boolean).join(" · ") || "—"} ${r.condition ? "· " + r.condition : ""}</div>
                  <div class="record-sub">${r.plot} · ${r.species || "sp. ?"}  <span class="confidence-badge ${flag}" style="font-size:0.65rem;padding:2px 6px;margin-left:4px">${flagEmoji(flag)} ${flag}</span></div>
                </div>
                <button class="btn btn-danger btn-sm btn-icon" title="Excluir" onclick="adminDeleteRecord(${r.id})">🗑</button>
              </div>`;
          }).join("")}
        </div>`;
      $("admin-by-observer").appendChild(obsCard);
    }
  } catch (e) {
    $("admin-campaign-info").innerHTML = `<p style="color:var(--red)">Erro ao carregar: ${e.message}</p>`;
    toast("Erro admin: " + e.message, "error");
  }
}

async function adminDeleteRecord(id) {
  if (!confirm("Excluir este registro da campanha?")) return;
  try {
    await fetch(`/api/records/${id}`, { method: "DELETE" });
    toast("Registro excluído");
    await openAdmin(State.currentCampaign.id);
  } catch (e) {
    toast("Erro ao excluir: " + e.message, "error");
  }
}

async function adminValidate() {
  if (!State.currentCampaign) return;
  $("admin-validate-btn").disabled = true;
  $("admin-validate-btn").textContent = "Validando…";
  $("admin-report").innerHTML = `<div style="display:flex;justify-content:center;padding:24px"><div class="loading-spinner"></div></div>`;
  try {
    const result = await api("POST", `/api/campaigns/${State.currentCampaign.id}/validate`);
    $("admin-report").innerHTML = `
      <div class="card" style="border-color:var(--border-hi)">
        <div class="card-header">
          <span class="card-title">Relatório de validação</span>
          <span class="confidence-badge ${result.errors > 0 ? 'erro' : result.warnings > 0 ? 'revisar' : 'ok'}">
            ${result.errors} erros · ${result.warnings} avisos
          </span>
        </div>
        <div class="report-content">${renderMarkdown(result.report_md)}</div>
      </div>`;
    toast(`Validação: ${result.errors} erro(s), ${result.warnings} aviso(s)`,
          result.errors > 0 ? "error" : result.warnings > 0 ? "warn" : "success");
    await openAdmin(State.currentCampaign.id);
  } catch (e) {
    $("admin-report").innerHTML = `<p style="color:var(--red)">Erro: ${e.message}</p>`;
    toast("Validação falhou: " + e.message, "error");
  } finally {
    $("admin-validate-btn").disabled = false;
    $("admin-validate-btn").textContent = "▶ Validar campanha";
  }
}

function adminExport() {
  if (!State.currentCampaign) return;
  const a = document.createElement("a");
  a.href = `/api/campaigns/${State.currentCampaign.id}/export`;
  a.click();
}

// ─── Tela SESSION SETUP ───────────────────────────────────────────────────────

async function selectCampaign(id) {
  try {
    State.currentCampaign = await api("GET", `/api/campaigns/${id}`);
    showScreen("session-setup");
    $("setup-campaign-name").textContent =
      `${State.currentCampaign.project_id} / ${State.currentCampaign.campaign_id}`;
    $("setup-date").value = State.session.date;
    $("setup-observer").value = State.session.observer;
    $("setup-plot").value = State.session.plot;
  } catch (e) {
    toast("Erro ao abrir campanha: " + e.message, "error");
  }
}

function startSession() {
  const observer = $("setup-observer").value.trim();
  const plot     = $("setup-plot").value.trim();
  const date     = $("setup-date").value.trim();
  if (!observer) { toast("Informe o observador", "warn"); return; }
  if (!plot)     { toast("Informe a parcela", "warn"); return; }
  if (!date)     { toast("Informe a data", "warn"); return; }

  State.session = { observer, plot, date };
  showScreen("main");
  updateSessionHeader();
  switchTab("collect");
  loadRecords();
}

function updateSessionHeader() {
  const c = State.currentCampaign;
  $("session-title").textContent =
    `${c.campaign_id} · ${State.session.plot}`;
  $("session-observer-badge").textContent = State.session.observer;
}

// ─── Tela MAIN (tabs: coletar / registros / validar) ─────────────────────────

function switchTab(tab) {
  State.activeTab = tab;
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.add("active");
  document.querySelector(`.tab-panel[data-tab="${tab}"]`).classList.add("active");

  if (tab === "records") loadRecords();
  if (tab === "validate") renderValidateTab();
}

// ─── Tab COLLECT ──────────────────────────────────────────────────────────────

function initSpeechRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const sr = new SR();
  sr.lang = "pt-BR";
  sr.continuous = false;
  sr.interimResults = true;
  sr.maxAlternatives = 3;

  sr.onresult = (event) => {
    let interim = "", final = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const t = event.results[i][0].transcript;
      if (event.results[i].isFinal) final += t;
      else interim += t;
    }
    if (final) {
      State.currentTranscript = (State.currentTranscript + " " + final).trim();
    }
    setTranscriptDisplay(State.currentTranscript || interim, !!final);
  };

  sr.onerror = (e) => {
    if (e.error !== "aborted") toast("Web Speech: " + e.error, "warn");
    setMicState("idle");
  };

  sr.onend = () => {
    if (State.isRecording) {
      // Reinicia automaticamente (frases longas)
      try { sr.start(); } catch (_) { setMicState("idle"); }
    }
  };
  return sr;
}

function setMicState(state) {
  const btn = $("mic-btn");
  btn.classList.remove("recording", "processing");
  const icon = $("mic-icon");
  const status = $("mic-status");
  if (state === "recording") {
    btn.classList.add("recording");
    icon.textContent = "⏹";
    status.textContent = "Gravando… toque para parar";
    State.isRecording = true;
  } else if (state === "processing") {
    btn.classList.add("processing");
    icon.textContent = "⏳";
    status.textContent = "Transcrevendo…";
    State.isRecording = false;
  } else {
    icon.textContent = "🎙";
    status.textContent = "Toque para gravar";
    State.isRecording = false;
  }
}

function setTranscriptDisplay(text, isFinal = false) {
  const el = $("transcript-display");
  if (!text) {
    el.textContent = "A transcrição aparecerá aqui…";
    el.classList.add("empty");
    el.classList.remove("active", "ready");
    return;
  }
  el.textContent = text;
  el.classList.remove("empty");
  if (isFinal) {
    el.classList.remove("active");
    el.classList.add("ready");
  } else {
    el.classList.add("active");
    el.classList.remove("ready");
  }
}

async function toggleMic() {
  if (State.isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  State.currentTranscript = "";
  State.parsedRecord = null;
  State.audioBlob = null;
  State.audioFilename = null;
  clearParsedFields();
  setTranscriptDisplay("");

  // Tenta Web Speech API primeiro
  State.speechRecognition = initSpeechRecognition();

  if (State.speechRecognition) {
    setMicState("recording");
    try {
      State.speechRecognition.start();
      // Também grava áudio em paralelo para evidência documental
      await startAudioCapture();
    } catch (e) {
      toast("Erro ao iniciar microfone: " + e.message, "error");
      setMicState("idle");
    }
  } else {
    // Sem Web Speech API: grava e envia para servidor transcrever
    toast("Web Speech não disponível — usando transcrição no servidor", "warn", 4000);
    setMicState("recording");
    await startAudioCapture();
  }
}

async function startAudioCapture() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = [];
    State.mediaRecorder = new MediaRecorder(stream, { mimeType: getPreferredMime() });
    State.mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
    State.mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop());
      State.audioBlob = new Blob(chunks, { type: State.mediaRecorder.mimeType });
      if (!State.speechRecognition) {
        // Envia para servidor transcrever com Whisper
        await serverTranscribe(State.audioBlob);
      } else {
        // Áudio ficou salvo apenas como evidência; já temos a transcrição via Web Speech
        await parseCurrentTranscript();
      }
    };
    State.mediaRecorder.start(250);
  } catch (e) {
    toast("Microfone: " + e.message, "error");
    setMicState("idle");
  }
}

function getPreferredMime() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find(t => MediaRecorder.isTypeSupported(t)) || "";
}

function stopRecording() {
  State.isRecording = false;
  if (State.speechRecognition) {
    try { State.speechRecognition.stop(); } catch (_) {}
    State.speechRecognition = null;
  }
  if (State.mediaRecorder && State.mediaRecorder.state !== "inactive") {
    State.mediaRecorder.stop();
    setMicState("processing");
  } else {
    setMicState("idle");
    parseCurrentTranscript();
  }
}

async function serverTranscribe(blob) {
  setMicState("processing");
  try {
    const form = new FormData();
    form.append("audio", blob, "audio.webm");
    form.append("language", "pt");
    const res = await fetch("/api/transcribe", { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).detail);
    const data = await res.json();
    State.currentTranscript = data.text;
    setTranscriptDisplay(data.text, true);
    await parseCurrentTranscript();
  } catch (e) {
    toast("Transcrição falhou: " + e.message, "error");
    setMicState("idle");
  }
}

async function parseCurrentTranscript() {
  const text = State.currentTranscript.trim() || $("transcript-display").textContent.trim();
  if (!text || text === "A transcrição aparecerá aqui…") {
    setMicState("idle");
    toast("Nenhum texto para interpretar", "warn");
    return;
  }
  setMicState("processing");
  try {
    const result = await api("POST", "/api/parse", {
      text,
      defaults: {
        project_id:  State.currentCampaign.project_id,
        campaign_id: State.currentCampaign.campaign_id,
        area:        State.currentCampaign.area,
        plot:        State.session.plot,
        observer:    State.session.observer,
        date:        State.session.date,
      },
    });
    State.parsedRecord = result;
    renderParsedFields(result);

    // Salva áudio no servidor como evidência documental
    if (State.audioBlob) {
      await uploadAudio(State.audioBlob);
    }
  } catch (e) {
    toast("Parse falhou: " + e.message, "error");
  } finally {
    setMicState("idle");
  }
}

async function uploadAudio(blob) {
  try {
    const form = new FormData();
    const ext  = blob.type.includes("ogg") ? ".ogg" : blob.type.includes("mp4") ? ".m4a" : ".webm";
    form.append("audio", blob, `audio${ext}`);
    const res = await api("POST", "/api/audio", form, true);
    State.audioFilename = res.filename;
  } catch (_) {
    // Falha no upload de áudio não bloqueia o registro
  }
}

function renderParsedFields(rec) {
  if (!rec || !rec.ok) {
    $("parsed-fields").innerHTML = `
      <div class="card" style="border-color:var(--red)">
        <p style="color:var(--red)">⚠ ${rec?.error || "Não foi possível interpretar a fala."}</p>
      </div>`;
    $("confirm-actions").classList.remove("hidden");
    return;
  }

  const flag = rec.confidence_flag || "ok";
  const flagBadge = `<span class="confidence-badge ${flag}">${flagEmoji(flag)} ${flag.toUpperCase()}</span>`;

  const fields = [
    { key: "tree_id",           label: "Árvore",      required: true },
    { key: "cap_cm",            label: "CAP (cm)",     src: rec.cap_source },
    { key: "dap_cm",            label: "DAP (cm)",     src: rec.dap_source },
    { key: "total_height_m",    label: "Altura total (m)" },
    { key: "crown_height_m",    label: "Alt. copa (m)" },
    { key: "crown_diameter_ns_m", label: "Copa N-S (m)" },
    { key: "crown_diameter_ew_m", label: "Copa L-O (m)" },
    { key: "species",           label: "Espécie" },
    { key: "condition",         label: "Condição" },
    { key: "observer",          label: "Observador" },
    { key: "date",              label: "Data" },
  ];

  const cells = fields.map(f => {
    const val = rec[f.key];
    const isDerived = f.src === "derived";
    const hasVal = val !== null && val !== undefined && val !== "";
    return `
      <div class="field-item ${hasVal ? (isDerived ? "derived" : "highlight") : ""}">
        <div class="field-label">${f.label}${isDerived ? " ↗" : ""}</div>
        <div class="field-value ${hasVal ? "" : "empty"}">${hasVal ? val : "—"}</div>
      </div>`;
  }).join("");

  const warnings = (rec.warnings || []).map(w =>
    `<div style="font-size:0.8rem;color:var(--amber);margin-top:6px">⚠ ${w}</div>`
  ).join("");

  $("parsed-fields").innerHTML = `
    <div class="card">
      <div class="card-header">
        <span class="card-title">Interpretado pelo morfocampo C++</span>
        ${flagBadge}
      </div>
      <div class="fields-grid">${cells}</div>
      ${warnings}
    </div>`;

  $("confirm-actions").classList.remove("hidden");
}

function flagEmoji(flag) {
  return { ok: "✓", revisar: "⚠", incompleto: "◌", erro: "✗" }[flag] || "?";
}

function clearParsedFields() {
  $("parsed-fields").innerHTML = "";
  $("confirm-actions").classList.add("hidden");
}

async function confirmRecord() {
  if (!State.parsedRecord || !State.parsedRecord.ok) {
    toast("Nada para confirmar", "warn"); return;
  }

  // Garante que observer e sessão estão no registro
  const rec = {
    ...State.parsedRecord,
    observer: State.session.observer,
    plot:     State.session.plot,
    date:     State.session.date,
    source:   "web_voice",
  };

  try {
    await api("POST", "/api/records", {
      campaign_id:    State.currentCampaign.id,
      parsed:         rec,
      audio_filename: State.audioFilename,
    });
    toast(`Árvore ${rec.tree_id || "?"} salva!`);
    clearParsedFields();
    setTranscriptDisplay("");
    State.parsedRecord = null;
    State.audioBlob = null;
    State.audioFilename = null;
    State.currentTranscript = "";
    // Atualiza contador
    await loadRecords();
  } catch (e) {
    toast("Erro ao salvar: " + e.message, "error");
  }
}

function discardRecord() {
  clearParsedFields();
  setTranscriptDisplay("");
  State.parsedRecord = null;
  State.audioBlob = null;
  State.currentTranscript = "";
}

async function parseManualText() {
  const text = $("manual-input").value.trim();
  if (!text) { toast("Digite uma frase primeiro", "warn"); return; }
  State.currentTranscript = text;
  setTranscriptDisplay(text, true);
  $("manual-input").value = "";
  await parseCurrentTranscript();
}

// ─── Tab RECORDS ──────────────────────────────────────────────────────────────

async function loadRecords() {
  if (!State.currentCampaign) return;
  try {
    // Registros exclusivos do observador atual
    const data = await api(
      "GET",
      `/api/campaigns/${State.currentCampaign.id}/records?observer=${encodeURIComponent(State.session.observer)}`
    );
    State.records = data.records;
    renderRecordList(data.records);
    $("records-count").textContent = data.total;
  } catch (e) {
    toast("Erro ao carregar registros: " + e.message, "error");
  }
}

function renderRecordList(records) {
  const list = $("records-list");
  if (!records.length) {
    list.innerHTML = `
      <div class="empty-state">
        <div class="icon">📋</div>
        <p>Nenhum registro ainda.<br>Vá para <strong>Coletar</strong> para adicionar.</p>
      </div>`;
    return;
  }

  list.innerHTML = records.map(r => {
    const flag = r.confidence_flag || "ok";
    const cls  = flag === "erro" ? "has-error" : flag !== "ok" ? "has-warn" : "ok";
    const cap  = r.cap_cm ? `CAP ${r.cap_cm.toFixed(1)} cm` : "";
    const dap  = r.dap_cm ? `DAP ${r.dap_cm.toFixed(1)} cm` : "";
    const meas = [cap, dap].filter(Boolean).join(" · ");
    return `
      <div class="record-item ${cls}" id="rec-${r.id}">
        <div class="record-id">${r.tree_id || "—"}</div>
        <div class="record-info">
          <div class="record-main">${meas || "—"} ${r.condition ? "· " + r.condition : ""}</div>
          <div class="record-sub">${r.plot} · ${r.species || "sp. ?"}
            <span class="confidence-badge ${flag}" style="font-size:0.65rem;padding:2px 6px;margin-left:6px">
              ${flagEmoji(flag)} ${flag}
            </span>
          </div>
        </div>
        <div class="record-actions">
          <button class="btn btn-ghost btn-sm btn-icon" title="Corrigir"
                  onclick="editRecord(${r.id})">✏️</button>
          <button class="btn btn-danger btn-sm btn-icon" title="Excluir"
                  onclick="deleteRecord(${r.id})">🗑</button>
        </div>
      </div>`;
  }).join("");
}

async function editRecord(id) {
  const rec = State.records.find(r => r.id === id);
  if (!rec) return;

  // Inline edit: preenche transcript com raw_input e re-interpreta
  $("transcript-display").textContent = rec.raw_input || "";
  $("transcript-display").classList.remove("empty", "active");
  $("transcript-display").classList.add("ready");
  State.currentTranscript = rec.raw_input || "";
  switchTab("collect");
  toast(`Editando árvore ${rec.tree_id} — corrija e confirme`, "warn", 5000);

  // Apaga o registro antigo e re-cria após confirmação
  await deleteRecord(id, true);
  await parseCurrentTranscript();
}

async function deleteRecord(id, silent = false) {
  if (!silent && !confirm("Excluir este registro?")) return;
  try {
    await fetch(`/api/records/${id}`, { method: "DELETE" });
    if (!silent) toast("Registro excluído");
    await loadRecords();
  } catch (e) {
    toast("Erro ao excluir: " + e.message, "error");
  }
}

// ─── Tab VALIDATE ─────────────────────────────────────────────────────────────

function renderValidateTab() {
  $("validate-campaign-name").textContent =
    `${State.currentCampaign.project_id} / ${State.currentCampaign.campaign_id}`;
}

async function runValidation() {
  $("validate-btn").disabled = true;
  $("validate-btn").textContent = "Validando…";
  $("report-container").innerHTML = `
    <div style="display:flex;justify-content:center;padding:32px">
      <div class="loading-spinner"></div>
    </div>`;

  try {
    const result = await api("POST", `/api/campaigns/${State.currentCampaign.id}/validate`);
    renderValidationResult(result);
    toast(`Validação concluída: ${result.errors} erro(s), ${result.warnings} aviso(s)`,
          result.errors > 0 ? "error" : result.warnings > 0 ? "warn" : "success");
  } catch (e) {
    $("report-container").innerHTML = `<p style="color:var(--red)">Erro: ${e.message}</p>`;
    toast("Validação falhou: " + e.message, "error");
  } finally {
    $("validate-btn").disabled = false;
    $("validate-btn").textContent = "▶ Validar campanha";
  }
}

function renderValidationResult(result) {
  const statsHtml = `
    <div class="stats-row" style="margin-bottom:16px">
      <div class="stat-box">
        <div class="stat-num blue">${result.total}</div>
        <div class="stat-label">Total</div>
      </div>
      <div class="stat-box">
        <div class="stat-num red">${result.errors}</div>
        <div class="stat-label">Erros</div>
      </div>
      <div class="stat-box">
        <div class="stat-num amber">${result.warnings}</div>
        <div class="stat-label">Avisos</div>
      </div>
    </div>`;

  const reportHtml = `
    <div class="report-content">
      ${renderMarkdown(result.report_md)}
    </div>`;

  $("report-container").innerHTML = statsHtml + reportHtml;
}

async function exportCampaign() {
  const url = `/api/campaigns/${State.currentCampaign.id}/export`;
  const a = document.createElement("a");
  a.href = url;
  a.download = "";
  a.click();
}

// ─── Init ─────────────────────────────────────────────────────────────────────

async function init() {
  showScreen("home");
  loadGlobalObserver();
  await loadCampaigns();

  // Checa status do servidor (binário C++ e transcrição)
  try {
    const status = await api("GET", "/api/status");
    if (!status.transcription.available) {
      toast(
        "Transcrição offline indisponível — usando Web Speech API do browser",
        "warn", 6000
      );
    }
  } catch (_) {}
}

document.addEventListener("DOMContentLoaded", init);
