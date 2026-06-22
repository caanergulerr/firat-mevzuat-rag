/**
 * app.js — Fırat Mevzuat RAG Frontend
 * FastAPI backend ile konuşan sohbet arayüzü
 *
 * API Endpoint: http://localhost:8000/query
 */

// Lokal geliştirme → localhost:8000 | Canlı → Hugging Face Spaces URL
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "https://baranarda-firat-mevzuat-rag.hf.space";  // ← HF Spaces URL (username-spacename.hf.space)

// ── DOM Referansları ───────────────────────────────────────────────────────────
const messagesContainer = document.getElementById("messagesContainer");
const welcomeScreen      = document.getElementById("welcomeScreen");
const questionInput      = document.getElementById("questionInput");
const sendBtn            = document.getElementById("sendBtn");
const statusDot          = document.getElementById("statusDot");
const systemStatus       = document.getElementById("systemStatus");
const newChatBtn         = document.getElementById("newChatBtn");

// ── Sistem Durumu ─────────────────────────────────────────────────────────────
let chatHistory = [];

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(120000) });
    const data = await res.json();

    if (data.index_ready) {
      statusDot.classList.remove("offline");
      systemStatus.textContent = "Sistem hazır";
    } else if (data.status === "loading") {
      statusDot.classList.add("offline");
      systemStatus.textContent = "Model yükleniyor...";
      // Yükleme sırasında daha sık kontrol et
      setTimeout(checkHealth, 10000);
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
    <div class="avatar user">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
      </svg>
    </div>
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
    <div class="avatar ai">
      <span class="avatar-text">FÜ</span>
    </div>
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

function startStreamingAIMessage() {
  removeTypingIndicator();
  const row = document.createElement("div");
  row.className = "message-row";
  
  row.innerHTML = `
    <div class="avatar ai">
      <span class="avatar-text">FÜ</span>
    </div>
    <div class="bubble ai streaming">
      <span class="cursor"></span>
    </div>
  `;
  messagesContainer.appendChild(row);
  scrollToBottom();
  
  return { row, bubble: row.querySelector(".bubble") };
}

function finalizeAIMessage(row, bubble, question, answer, sources, latencyMs) {
  bubble.classList.remove("streaming");
  
  let sourcesHtml = "";
  if (sources && sources.length > 0) {
    const items = sources.map((s, idx) => {
      const sourceId = Date.now() + "_" + idx;
      window.sourceData = window.sourceData || {};
      window.sourceData[sourceId] = { title: s.citation, text: s.text };
      return `<div class="source-badge" style="display:inline-block; padding:4px 8px; border-radius:12px; background:rgba(123, 13, 30, 0.08); font-size:12px; font-weight:500; color:#7b0d1e; border:1px solid rgba(123, 13, 30, 0.2);" onclick="openSourceModal('${sourceId}')">📄 ${escapeHtml(s.citation)}</div>`;
    }).join("");
    sourcesHtml = `
      <div class="sources-block" style="animation: fadeIn 0.5s; margin-top:12px;">
        <div class="sources-label" style="font-size:11px; font-weight:600; color:#64748b; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">Kaynaklar (Tıklayarak Oku)</div>
        <div class="sources-list" style="display:flex; flex-wrap:wrap; gap:8px;">
          ${items}
        </div>
      </div>
    `;
  }

  let metaHtml = latencyMs
    ? `<div style="font-size:11px;color:#475569;margin-top:8px;">${latencyMs}ms</div>`
    : "";

  const feedbackHtml = `
    <div class="feedback-container" style="animation: fadeIn 0.5s;">
      <button class="feedback-btn like-btn" title="Beğendim">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
        </svg>
        Beğendim
      </button>
      <button class="feedback-btn dislike-btn" title="Beğenmedim">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
        </svg>
        Beğenmedim
      </button>
    </div>
  `;

  bubble.innerHTML = `
    ${formatAnswer(answer)}
    ${sourcesHtml}
    ${feedbackHtml}
    ${metaHtml}
  `;
  
  const likeBtn = row.querySelector(".like-btn");
  const dislikeBtn = row.querySelector(".dislike-btn");

  const handleFeedback = async (rating) => {
    likeBtn.disabled = true;
    dislikeBtn.disabled = true;
    
    if (rating === "like") {
      likeBtn.classList.add("active-like");
      try {
        await fetch(`${API_BASE}/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, answer, rating }),
        });
      } catch (e) {
        console.error("Geri bildirim gönderilemedi:", e);
      }
    } else {
      dislikeBtn.classList.add("active-dislike");
      
      const formContainer = document.createElement("div");
      formContainer.className = "detailed-feedback-form";
      formContainer.innerHTML = `
        <div style="font-size:0.9rem;font-weight:600;color:#334155;margin-bottom:8px;">Neyi beğenmediniz?</div>
        <div class="feedback-reasons">
          <button class="feedback-reason-btn">Yanlış Bilgi</button>
          <button class="feedback-reason-btn">Eksik Kaynak</button>
          <button class="feedback-reason-btn">Anlaşılmaz Cevap</button>
          <button class="feedback-reason-btn">Diğer</button>
        </div>
        <textarea class="feedback-comment" placeholder="Varsa eklemek istediklerinizi yazın..."></textarea>
        <div class="feedback-actions">
          <button class="btn-cancel-feedback">İptal</button>
          <button class="btn-submit-feedback">Gönder</button>
        </div>
      `;
      
      bubble.appendChild(formContainer);
      scrollToBottom();
      
      let selectedReason = null;
      const reasonBtns = formContainer.querySelectorAll(".feedback-reason-btn");
      reasonBtns.forEach(btn => {
        btn.addEventListener("click", () => {
          reasonBtns.forEach(b => b.classList.remove("selected"));
          btn.classList.add("selected");
          selectedReason = btn.textContent;
        });
      });
      
      const cancelBtn = formContainer.querySelector(".btn-cancel-feedback");
      const submitBtn = formContainer.querySelector(".btn-submit-feedback");
      const commentEl = formContainer.querySelector(".feedback-comment");
      
      cancelBtn.addEventListener("click", () => {
        formContainer.remove();
        dislikeBtn.classList.remove("active-dislike");
        likeBtn.disabled = false;
        dislikeBtn.disabled = false;
      });
      
      submitBtn.addEventListener("click", async () => {
        submitBtn.disabled = true;
        submitBtn.textContent = "Gönderiliyor...";
        try {
          await fetch(`${API_BASE}/feedback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
              question, 
              answer, 
              rating,
              reason: selectedReason,
              comment: commentEl.value
            }),
          });
          formContainer.innerHTML = `<div style="color:#10b981;font-weight:500;font-size:0.9rem;">Geri bildiriminiz için teşekkürler! 🙏</div>`;
          setTimeout(() => formContainer.remove(), 3000);
        } catch (e) {
          console.error("Geri bildirim gönderilemedi:", e);
          submitBtn.disabled = false;
          submitBtn.textContent = "Gönder";
        }
      });
    }
  };

  likeBtn.addEventListener("click", () => handleFeedback("like"));
  dislikeBtn.addEventListener("click", () => handleFeedback("dislike"));

  chatHistory.push({ role: "user", content: question });
  chatHistory.push({ role: "assistant", content: answer });

  scrollToBottom();
}

function appendErrorMessage(msg) {
  removeTypingIndicator();
  const row = document.createElement("div");
  row.className = "message-row";
  row.innerHTML = `
    <div class="avatar ai">
      <span class="avatar-text">FÜ</span>
    </div>
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
      body: JSON.stringify({ 
        question, 
        top_k: 5,
        history: chatHistory.slice(-6)
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      let err;
      try { err = JSON.parse(errText); } catch(e) { err = { detail: errText }; }
      throw new Error(err.detail || `Sunucu hatası: ${res.status}`);
    }

    const { row, bubble } = startStreamingAIMessage();
    let answerText = "";
    let sources = [];
    let latencyMs = 0;
    
    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      let lines = buffer.split('\n');
      
      // Son satır yarım kalmış olabilir
      buffer = lines.pop();

      for (let line of lines) {
        line = line.trim();
        if (line.startsWith("data: ")) {
          const dataStr = line.slice(6).trim();
          if (dataStr === "[DONE]") {
            finalizeAIMessage(row, bubble, question, answerText, sources, latencyMs);
            break;
          }
          if (dataStr.startsWith("{")) {
            try {
              const data = JSON.parse(dataStr);
              if (data.type === "content") {
                answerText += data.text;
                bubble.innerHTML = formatAnswer(answerText) + '<span class="cursor"></span>';
                scrollToBottom();
                await new Promise(r => setTimeout(r, 30)); // Yazı akış hızını ayarla (30ms)
              } else if (data.type === "meta") {
                sources = data.sources;
                latencyMs = data.latency_ms;
              }
            } catch (e) {
              console.error("Stream parse hatası:", e);
            }
          }
        }
      }
    }

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

// ── Modal İşlemleri ──────────────────────────────────────────────────────────
const sourceModal = document.getElementById("sourceModal");
const closeModalBtn = document.getElementById("closeModalBtn");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");

window.openSourceModal = function(sourceId) {
  const data = window.sourceData[sourceId];
  if (!data) return;
  modalTitle.textContent = data.title;
  modalBody.innerHTML = formatAnswer(data.text);
  sourceModal.style.display = "block";
};

closeModalBtn.addEventListener("click", () => {
  sourceModal.style.display = "none";
});

window.addEventListener("click", (e) => {
  if (e.target === sourceModal) {
    sourceModal.style.display = "none";
  }
});

questionInput.addEventListener("input", adjustTextareaHeight);

// ── Accordion Menü Mantığı ──────────────────────────────────────────────────
document.querySelectorAll(".accordion-header").forEach(header => {
  header.addEventListener("click", () => {
    const item = header.parentElement;
    const content = header.nextElementSibling;
    
    // Açık olan diğerlerini kapat
    document.querySelectorAll(".accordion-item.active").forEach(activeItem => {
      if (activeItem !== item) {
        activeItem.classList.remove("active");
        activeItem.querySelector(".accordion-content").style.maxHeight = null;
      }
    });

    // Tıklananı aç/kapat
    item.classList.toggle("active");
    if (item.classList.contains("active")) {
      content.style.maxHeight = content.scrollHeight + "px";
    } else {
      content.style.maxHeight = null;
    }
  });
});

// İlk menüyü varsayılan olarak aç
setTimeout(() => {
  const firstAccordion = document.querySelector(".accordion-item");
  if (firstAccordion) {
    firstAccordion.classList.add("active");
    const content = firstAccordion.querySelector(".accordion-content");
    content.style.maxHeight = content.scrollHeight + "px";
  }
}, 100);

// Örnek sorular
document.querySelectorAll(".example-q").forEach((btn) => {
  btn.addEventListener("click", () => {
    const q = btn.dataset.q;
    questionInput.value = q;
    adjustTextareaHeight();
    sendQuestion(q);
    
    // Mobil görünümde menüyü kapatmak istenirse eklenebilir
    // document.querySelector(".app-container").classList.remove("menu-open");
  });
});

// Yeni sohbet
newChatBtn.addEventListener("click", () => {
  chatHistory = [];
  messagesContainer.innerHTML = "";
  const welcome = document.createElement("div");
  welcome.className = "welcome-screen";
  welcome.id = "welcomeScreen";
  welcome.innerHTML = `
    <div class="welcome-icon-wrapper">
      <span class="welcome-text-logo">FÜ</span>
      <div class="icon-glow" style="background: rgba(123, 13, 30, 0.2);"></div>
    </div>
    <h1 class="welcome-title">Nasıl yardımcı olabilirim?</h1>
    <p class="welcome-subtitle">
      Fırat Üniversitesi yönetmeliklerine dair tüm sorularınızı sorun.<br/>
      Her yanıtın altında ilgili resmi madde referansı gösterilir.
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
