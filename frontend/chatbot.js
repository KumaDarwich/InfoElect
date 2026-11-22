/**
 * InfoElect Impartial Comparative Chatbot Widget
 * Anchored bottom-right; compares all 4 official 29N 2026 electoral programs
 * strictly without opinions, rankings, or voting advice.
 */

const STARTER_PROMPTS = [
  "¿Qué diferencias hay en las pensiones?",
  "Compara las propuestas de vivienda y alquiler",
  "¿Qué propone cada partido sobre impuestos (IRPF e IVA)?",
  "Diferencias en inmigración y fronteras",
  "¿Qué dicen sobre sanidad y listas de espera?",
  "Diferencias en energía nuclear y transición ecológica",
];

const PARTY_COLORS = {
  frente_amplio: "#EA4C1D",
  pp: "#0056A3",
  psoe: "#E30613",
  vox: "#5BB318",
};

export class ImpartialChatbot {
  constructor({ onOpenSource }) {
    this.onOpenSource = onOpenSource;
    this.isOpen = false;
    this.isExpanded = false;
    this.selectedParties = new Set(); // empty => all 4 parties
    this.busy = false;

    this.widgetEl = document.getElementById("chatbotWidget");
    this.bubbleBtn = document.getElementById("chatBubbleBtn");
    this.panelEl = document.getElementById("chatPanel");
    this.messagesEl = document.getElementById("chatMessages");
    this.inputForm = document.getElementById("chatInputForm");
    this.inputEl = document.getElementById("chatInput");
    this.closeBtn = document.getElementById("chatCloseBtn");
    this.expandBtn = document.getElementById("chatExpandBtn");
    this.resetBtn = document.getElementById("chatResetBtn");
    this.filterEl = document.getElementById("chatPartyFilter");

    this._bindEvents();
    this.renderWelcome();
  }

  _bindEvents() {
    this.bubbleBtn.addEventListener("click", () => this.toggle());
    this.closeBtn.addEventListener("click", () => this.close());
    this.expandBtn.addEventListener("click", () => {
      this.isExpanded = !this.isExpanded;
      this.panelEl.classList.toggle("expanded", this.isExpanded);
      this.expandBtn.textContent = this.isExpanded ? "⤡" : "⤢";
      this.expandBtn.title = this.isExpanded ? "Reducir ventana" : "Ampliar ventana";
    });
    this.resetBtn.addEventListener("click", () => this.renderWelcome());

    this.filterEl.addEventListener("click", (e) => {
      const chip = e.target.closest(".chat-party-chip");
      if (!chip) return;
      const pid = chip.dataset.party;
      if (pid === "all") {
        this.selectedParties.clear();
      } else {
        if (this.selectedParties.has(pid)) {
          this.selectedParties.delete(pid);
        } else {
          this.selectedParties.add(pid);
        }
        if (this.selectedParties.size === 4) {
          this.selectedParties.clear();
        }
      }
      this._syncFilterChips();
    });

    this.inputForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = this.inputEl.value.trim();
      if (!text || this.busy) return;
      this.inputEl.value = "";
      this.ask(text);
    });
  }

  _syncFilterChips() {
    const chips = this.filterEl.querySelectorAll(".chat-party-chip");
    const isAll = this.selectedParties.size === 0;
    chips.forEach((chip) => {
      const pid = chip.dataset.party;
      if (pid === "all") {
        chip.classList.toggle("active", isAll);
      } else {
        chip.classList.toggle("active", !isAll && this.selectedParties.has(pid));
      }
    });
  }

  open() {
    this.isOpen = true;
    this.widgetEl.classList.add("open");
    this.panelEl.hidden = false;
    this.bubbleBtn.setAttribute("aria-expanded", "true");
    setTimeout(() => this.inputEl.focus(), 120);
  }

  close() {
    this.isOpen = false;
    this.widgetEl.classList.remove("open");
    this.panelEl.hidden = true;
    this.bubbleBtn.setAttribute("aria-expanded", "false");
  }

  toggle() {
    if (this.isOpen) this.close();
    else this.open();
  }

  openAndAsk(question) {
    this.open();
    this.ask(question);
  }

  renderWelcome() {
    this.messagesEl.innerHTML = "";
    const msg = document.createElement("div");
    msg.className = "chat-msg bot";
    msg.innerHTML = `
      <div class="msg-bubble">
        <div class="impartial-notice-box">
          ⚖️ <strong>Modo estrictamente imparcial:</strong> respondo únicamente con datos y diferencias verificables de los 4 programas electorales descargados (29N 2026), sin opiniones ni recomendaciones de voto.
        </div>
        <p class="bot-intro">
          Pregúntame qué propone cada partido o en qué se diferencian sobre cualquier tema. Puedes pulsar uno de estos ejemplos o escribir tu propia consulta:
        </p>
        <div class="chat-suggestions">
          ${STARTER_PROMPTS.map(
            (p) => `<button type="button" class="chat-suggestion-chip">${this._escape(p)}</button>`
          ).join("")}
        </div>
      </div>
    `;
    msg.querySelectorAll(".chat-suggestion-chip").forEach((btn) => {
      btn.addEventListener("click", () => this.ask(btn.textContent));
    });
    this.messagesEl.appendChild(msg);
  }

  async ask(question) {
    if (this.busy) return;
    this.busy = true;

    // Render user bubble
    const userMsg = document.createElement("div");
    userMsg.className = "chat-msg user";
    userMsg.innerHTML = `<div class="msg-bubble">${this._escape(question)}</div>`;
    this.messagesEl.appendChild(userMsg);

    // Render loading indicator
    const loadingMsg = document.createElement("div");
    loadingMsg.className = "chat-msg bot";
    loadingMsg.innerHTML = `
      <div class="msg-bubble">
        <div class="typing-dots" aria-label="Comparando programas...">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
    this.messagesEl.appendChild(loadingMsg);
    this._scrollToBottom();

    try {
      const payload = {
        message: question,
        parties: this.selectedParties.size > 0 ? Array.from(this.selectedParties) : null,
      };
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      loadingMsg.remove();
      const botNode = this._renderBotResponse(data);
      requestAnimationFrame(() => {
        if (botNode) {
          this.messagesEl.scrollTop = Math.max(0, botNode.offsetTop - 12);
        }
      });
    } catch (err) {
      loadingMsg.remove();
      const errEl = document.createElement("div");
      errEl.className = "chat-msg bot";
      errEl.innerHTML = `
        <div class="msg-bubble">
          No se pudo consultar el comparador en este momento. Comprueba que el servidor de InfoElect esté activo.
        </div>
      `;
      this.messagesEl.appendChild(errEl);
      this._scrollToBottom();
    } finally {
      this.busy = false;
    }
  }

  _renderBotResponse(data) {
    const wrapper = document.createElement("div");
    wrapper.className = "chat-msg bot";
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    let html = "";

    if (data.impartial_notice) {
      html += `<div class="impartial-notice-box">⚖️ ${this._escape(data.impartial_notice)}</div>`;
    }

    if (data.intro) {
      html += `<p class="bot-intro">${this._formatBold(data.intro)}</p>`;
    }

    if (data.key_differences && data.key_differences.length > 0) {
      html += `
        <div class="diff-box">
          <div class="diff-box-title">Ejes objetivos de diferencia</div>
          <ul>
            ${data.key_differences.map((d) => `<li>${this._formatBold(d)}</li>`).join("")}
          </ul>
        </div>
      `;
    }

    if (data.party_comparisons && data.party_comparisons.length > 0) {
      html += `<div class="party-compare-stack">`;
      for (const pc of data.party_comparisons) {
        const color = pc.color || PARTY_COLORS[pc.party] || "#0F172A";
        const mutedCls = pc.has_coverage === false ? "muted" : "";
        html += `
          <article class="party-compare-card ${mutedCls}" style="--card-color:${color}">
            <div class="party-compare-head">
              <strong>${this._escape(pc.party_name)}</strong>
              <small>${this._escape(pc.program_title || "")}</small>
            </div>
            <p class="party-compare-summary">${this._formatBold(pc.summary)}</p>
            ${
              pc.points && pc.points.length
                ? `<ul class="party-compare-points">${pc.points
                    .map((pt) => `<li>${this._formatBold(pt)}</li>`)
                    .join("")}</ul>`
                : ""
            }
            ${
              pc.citations && pc.citations.length
                ? `<div class="party-citations-row">
                    ${pc.citations
                      .slice(0, 4)
                      .map(
                        (c) =>
                          `<button type="button" class="mini-cite-btn" data-party="${pc.party}" data-pdf-page="${c.pdf_page}" title="Ver página original del PDF">📄 pág. ${c.doc_page}</button>`
                      )
                      .join("")}
                  </div>`
                : ""
            }
          </article>
        `;
      }
      html += `</div>`;
    }

    if (data.sources && data.sources.length > 0) {
      html += `
        <details class="sources-accordion">
          <summary>Ver fragmentos literales de los PDFs (${data.sources.length})</summary>
          <div class="sources-list">
            ${data.sources
              .map((s) => {
                const col = PARTY_COLORS[s.party] || "#334155";
                const excerpt = s.text.length > 290 ? s.text.slice(0, 290) + "…" : s.text;
                return `
                  <div class="source-quote-item" style="--quote-color:${col}">
                    <header>
                      <span>${this._escape(s.party_name)} · ${this._escape(s.section || "")}</span>
                      <button type="button" class="mini-cite-btn" data-party="${s.party}" data-pdf-page="${s.pdf_page}">pág. ${s.doc_page} ↗</button>
                    </header>
                    <div>«${this._escape(excerpt)}»</div>
                  </div>
                `;
              })
              .join("")}
          </div>
        </details>
      `;
    }

    if (data.suggested_followups && data.suggested_followups.length > 0) {
      html += `
        <div class="chat-suggestions">
          ${data.suggested_followups
            .slice(0, 3)
            .map((f) => `<button type="button" class="chat-suggestion-chip">${this._escape(f)}</button>`)
            .join("")}
        </div>
      `;
    }

    bubble.innerHTML = html;

    // Bind interactive citation & followup buttons
    bubble.querySelectorAll(".mini-cite-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.onOpenSource) {
          this.onOpenSource(btn.dataset.party, Number(btn.dataset.pdfPage));
        }
      });
    });

    bubble.querySelectorAll(".chat-suggestion-chip").forEach((btn) => {
      btn.addEventListener("click", () => this.ask(btn.textContent));
    });

    wrapper.appendChild(bubble);
    this.messagesEl.appendChild(wrapper);
    return wrapper;
  }

  _scrollToBottom() {
    requestAnimationFrame(() => {
      this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    });
  }

  _escape(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  _formatBold(str) {
    return this._escape(str)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+?)\*/g, "<em>$1</em>");
  }
}
