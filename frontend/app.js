/**
 * app.js — Fırat Mevzuat RAG Frontend
 * FastAPI backend ile konuşan sohbet arayüzü
 *
 * API Endpoint: http://localhost:8000/query
 */

const API_BASE = "http://localhost:8000";

// ── DOM Referansları ───────────────────────────────────────────────────────────
const messagesContainer = document.getElementById("messagesContainer");
const welcomeScreen      = document.getElementById("welcomeScreen");
const questionInput      = document.getElementById("questionInput");
const sendBtn            = document.getElementById("sendBtn");
const statusDot          = document.getElementById("statusDot");
const systemStatus       = document.getElementById("systemStatus");
const newChatBtn         = document.getElementById("newChatBtn");

// ── Sistem Durumu ─────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();

    if (data.index_ready) {
      statusDot.classList.remove("offline");
      systemStatus.textContent = "Sistem hazır";
    } else {
      statusDot.classList.add("offline");
      systemStatus.textContent = "Index bekleniyor";
    }
  } catch {
    statusDot.classList.add("offline");
    systemStatus.textContent = "API bağlantısı yok";
  }
}

// ── Mesaj Oluşturma ───────────────────────────────────────────────────────────
function hideWelcome() {
  if (welcomeScreen) welcomeScreen.style.display = "none";
}

function appendUserMessage(text) {
  hideWelcome();
  const row = document.createElement("div");
  row.className = "message-row user";
  row.innerHTML = `
    <div class="avatar user">🎓</div>
    <div class="bubble user">${escapeHtml(text)}</div>
  `;
  messagesContainer.appendChild(row);
  scrollToBottom();
}

function appendTypingIndicator() {
  const row = document.createElement("div");
  row.className = "message-row";
  row.id = "typingRow";
  row.innerHTML = `
    <div class="avatar ai">⚖️</div>
    <div class="typing-indicator">
      <div class="dot"></div>
      <div class="dot"></div>
      <div class="dot"></div>
    </div>
  `;
  messagesContainer.appendChild(row);
  scrollToBottom();
}

function removeTypingIndicator() {
  const row = document.getElementById("typingRow");
  if (row) row.remove();
}

function appendAIMessage(answer, sources, latencyMs) {
  const row = document.createElement("div");
  row.className = "message-row";

  let sourcesHtml = "";
  if (sources && sources.length > 0) {
    const items = sources.map(s => `<div class="source-item">📖 ${escapeHtml(s)}</div>`).join("");
    sourcesHtml = `
      <div class="sources-block">
        <div class="sources-label">Kaynaklar</div>
        ${items}
      </div>
    `;
  }

  let metaHtml = latencyMs
    ? `<div style="font-size:11px;color:#475569;margin-top:8px;">${latencyMs}ms</div>`
    : "";

  row.innerHTML = `
    <div class="avatar ai">⚖️</div>
    <div class="bubble ai">
      ${formatAnswer(answer)}
      ${sourcesHtml}
      ${metaHtml}
    </div>
  `;
  messagesContainer.appendChild(row);
  scrollToBottom();
}

function appendErrorMessage(msg) {
  removeTypingIndicator();
  const row = document.createElement("div");
  row.className = "message-row";
  row.innerHTML = `
    <div class="avatar ai">⚖️</div>
    <div class="bubble ai" style="color:#f87171;">
      ⚠️ ${escapeHtml(msg)}
    </div>
  `;
  messagesContainer.appendChild(row);
  scrollToBottom();
}

// ── Yardımcı Fonksiyonlar ─────────────────────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

function formatAnswer(text) {
  // Basit Markdown: **bold**, yeni satır → <br>
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function scrollToBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function setLoading(loading) {
  sendBtn.disabled = loading;
  questionInput.disabled = loading;
}

// ── API Sorgusu ───────────────────────────────────────────────────────────────
async function sendQuestion(question) {
  if (!question.trim()) return;

  appendUserMessage(question);
  appendTypingIndicator();
  setLoading(true);
  questionInput.value = "";
  adjustTextareaHeight();

  try {
    const res = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 5 }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `Sunucu hatası: ${res.status}`);
    }

    const data = await res.json();
    removeTypingIndicator();
    appendAIMessage(data.answer, data.sources, data.latency_ms);

  } catch (err) {
    appendErrorMessage(
      err.message.includes("fetch")
        ? "API'ye bağlanılamadı. Backend çalışıyor mu? (uvicorn backend.api:app --reload)"
        : err.message
    );
  } finally {
    setLoading(false);
    questionInput.focus();
  }
}

// ── Textarea Otomatik Yükseklik ───────────────────────────────────────────────
function adjustTextareaHeight() {
  questionInput.style.height = "auto";
  questionInput.style.height = Math.min(questionInput.scrollHeight, 140) + "px";
}

// ── Event Listener'lar ────────────────────────────────────────────────────────
sendBtn.addEventListener("click", () => sendQuestion(questionInput.value));

questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendQuestion(questionInput.value);
  }
});

questionInput.addEventListener("input", adjustTextareaHeight);

// Örnek sorular
document.querySelectorAll(".example-q").forEach((btn) => {
  btn.addEventListener("click", () => {
    const q = btn.dataset.q;
    questionInput.value = q;
    adjustTextareaHeight();
    sendQuestion(q);
  });
});

// Yeni sohbet
newChatBtn.addEventListener("click", () => {
  messagesContainer.innerHTML = "";
  const welcome = document.createElement("div");
  welcome.className = "welcome-screen";
  welcome.id = "welcomeScreen";
  welcome.innerHTML = `
    <div class="welcome-icon">⚖️</div>
    <h1 class="welcome-title">Merhaba, nasıl yardımcı olabilirim?</h1>
    <p class="welcome-subtitle">
      Fırat Üniversitesi yönetmeliklerine dair sorularınızı sorun.<br/>
      Her yanıtın altında ilgili madde referansı gösterilir.
    </p>
  `;
  messagesContainer.appendChild(welcome);
  questionInput.value = "";
  questionInput.focus();
});

// ── Başlangıç ─────────────────────────────────────────────────────────────────
checkHealth();
setInterval(checkHealth, 30_000); // 30 saniyede bir kontrol
questionInput.focus();
