/**
 * InfoElect Main Application Controller
 * Connects the Party Bubble Selector, Interactive Radial Visual Map,
 * 4x1 Neutral Comparison Matrix, Full-Text PDF Search, Source Page Modal,
 * and Bottom-Right Impartial Comparative Chatbot.
 */

import { VisualMindMap } from "./mindmap.js";
import { ImpartialChatbot } from "./chatbot.js";

const state = {
  data: null,
  activeView: "selector",
  selectedPartyId: null,
  selectedDomainId: "economia",
  compareDomainId: "economia",
};

let mindmap = null;
let chatbot = null;

async function init() {
  try {
    const res = await fetch("/api/programs");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.data = await res.json();
  } catch (err) {
    document.getElementById("bubbleConstellation").innerHTML = `
      <p style="color:#b91c1c;font-weight:700;">
        Error cargando los programas electorales. Comprueba que el servidor de InfoElect esté ejecutándose.
      </p>
    `;
    return;
  }

  // Initialize Interactive Mind-Map
  mindmap = new VisualMindMap({
    viewportEl: document.getElementById("mindmapViewport"),
    stageEl: document.getElementById("mindmapStage"),
    svgEl: document.getElementById("mindmapSvg"),
    nodesEl: document.getElementById("mindmapNodes"),
    onSelectDomain: (domainId) => {
      state.selectedDomainId = domainId;
      renderMapWorkspace();
    },
  });

  // Initialize Bottom-Right Impartial Chatbot
  chatbot = new ImpartialChatbot({
    onOpenSource: (partyId, pdfPage) => openSourceModal(partyId, pdfPage),
  });

  bindGlobalEvents();
  document.body.classList.add("on-selector");
  renderPartyBubbles();
  renderHeaderDropdown();
  renderCompareView();

  // Zoom controls
  document.getElementById("mapZoomIn").addEventListener("click", () => mindmap.zoomBy(0.14));
  document.getElementById("mapZoomOut").addEventListener("click", () => mindmap.zoomBy(-0.14));
  document.getElementById("mapResetView").addEventListener("click", () => mindmap.resetView());

  // Optional URL query deep-linking (?party=pp&domain=economia&view=map&chat=...)
  const params = new URLSearchParams(window.location.search);
  const qDomain = params.get("domain");
  if (qDomain && state.data.domains.some((d) => d.id === qDomain)) {
    state.selectedDomainId = qDomain;
    state.compareDomainId = qDomain;
    renderCompareView();
  }
  const qParty = params.get("party");
  if (qParty && state.data.parties.some((p) => p.id === qParty)) {
    selectParty(qParty, true);
  }
  const qView = params.get("view");
  if (qView && ["selector", "map", "compare", "search"].includes(qView)) {
    if (qView === "map" && !state.selectedPartyId) {
      selectParty(state.data.parties[0].id, false);
    }
    switchView(qView);
  }
  const qChat = params.get("chat");
  if (qChat) {
    chatbot.openAndAsk(qChat);
  }
}

function bindGlobalEvents() {
  // Brand logo returns to bubble selector
  document.getElementById("brandHomeBtn").addEventListener("click", () => switchView("selector"));

  // Top view tabs
  document.querySelectorAll(".view-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.view;
      if (target === "map" && !state.selectedPartyId) {
        // Default neutrally to first alphabetical party if user clicks Mapa Visual directly
        selectParty(state.data.parties[0].id, false);
      }
      switchView(target);
    });
  });

  // Hero quick CTAs
  document.getElementById("jumpCompareBtn").addEventListener("click", () => switchView("compare"));
  document.getElementById("openChatFromHeroBtn").addEventListener("click", () => chatbot.open());

  // Header party switcher dropdown
  const pillTrigger = document.getElementById("partyPillTrigger");
  const dropdown = document.getElementById("partyDropdownBubbles");
  pillTrigger.addEventListener("click", (e) => {
    e.stopPropagation();
    const isHidden = dropdown.hidden;
    dropdown.hidden = !isHidden;
    pillTrigger.setAttribute("aria-expanded", String(isHidden));
  });
  document.addEventListener("click", () => {
    if (!dropdown.hidden) {
      dropdown.hidden = true;
      pillTrigger.setAttribute("aria-expanded", "false");
    }
  });

  // Compare view -> ask chatbot button
  document.getElementById("askDomainChatBtn").addEventListener("click", () => {
    const dom = state.data.domains.find((d) => d.id === state.compareDomainId);
    if (dom) {
      chatbot.openAndAsk(`¿Qué diferencias hay entre los 4 partidos en ${dom.label}?`);
    }
  });

  // PDF Full-text search
  const searchForm = document.getElementById("pdfSearchForm");
  const searchInput = document.getElementById("pdfSearchInput");
  const searchPartySelect = document.getElementById("pdfSearchPartyFilter");
  searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    runPdfSearch(searchInput.value.trim(), searchPartySelect.value);
  });
  searchPartySelect.addEventListener("change", () => {
    if (searchInput.value.trim().length >= 2) {
      runPdfSearch(searchInput.value.trim(), searchPartySelect.value);
    }
  });
  document.querySelectorAll("#searchQuickTags button").forEach((btn) => {
    btn.addEventListener("click", () => {
      searchInput.value = btn.dataset.q;
      runPdfSearch(btn.dataset.q, searchPartySelect.value);
    });
  });

  // Modals (Source Page & Impartiality)
  const sourceModal = document.getElementById("sourceModal");
  document.getElementById("sourceModalClose").addEventListener("click", () => (sourceModal.hidden = true));
  sourceModal.addEventListener("click", (e) => {
    if (e.target === sourceModal) sourceModal.hidden = true;
  });

  const neutralityModal = document.getElementById("neutralityModal");
  document.getElementById("neutralityInfoBtn").addEventListener("click", () => (neutralityModal.hidden = false));
  document.getElementById("neutralityModalClose").addEventListener("click", () => (neutralityModal.hidden = true));
  neutralityModal.addEventListener("click", (e) => {
    if (e.target === neutralityModal) neutralityModal.hidden = true;
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      sourceModal.hidden = true;
      neutralityModal.hidden = true;
    }
  });
}

function switchView(viewName) {
  state.activeView = viewName;
  document.body.classList.toggle("on-selector", viewName === "selector");
  document.querySelectorAll(".view-tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.view === viewName);
  });

  const mapIds = {
    selector: "viewSelector",
    map: "viewMap",
    compare: "viewCompare",
    search: "viewSearch",
  };

  Object.entries(mapIds).forEach(([key, elId]) => {
    document.getElementById(elId).classList.toggle("active", key === viewName);
  });

  if (viewName === "map" && state.selectedPartyId) {
    renderMapWorkspace();
    requestAnimationFrame(() => mindmap.fitToViewport(true));
  }
}

function applyPartyTheme(party) {
  const root = document.documentElement;
  root.style.setProperty("--active-party", party.color);
  root.style.setProperty("--active-party-soft", party.soft_color);
  root.style.setProperty("--active-party-ring", `${party.color}33`);

  document.getElementById("headerPartyLabel").textContent = party.name;
  document.getElementById("headerPartyDot").style.background = party.color;
}

function selectParty(partyId, goToMap = true) {
  const party = state.data.parties.find((p) => p.id === partyId);
  if (!party) return;
  state.selectedPartyId = partyId;
  applyPartyTheme(party);
  renderHeaderDropdown();
  renderMapPartyDock();
  if (goToMap) {
    switchView("map");
  } else {
    renderMapWorkspace();
  }
}

function renderPartyBubbles() {
  const container = document.getElementById("bubbleConstellation");
  container.innerHTML = "";

  state.data.parties.forEach((party, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "party-bubble-card";
    btn.setAttribute("role", "listitem");
    btn.style.setProperty("--bubble-color", party.color);
    btn.style.setProperty("--bubble-soft", party.soft_color);
    btn.style.setProperty("--float-delay", `${idx * 0.65}s`);

    btn.innerHTML = `
      <span class="party-bubble-emblem">${escapeHtml(party.short_code)}</span>
      <span class="party-bubble-name">${escapeHtml(party.name)}</span>
      <span class="party-bubble-slogan">«${escapeHtml(party.program_title)}»</span>
      <span class="party-bubble-meta">${party.pages} págs. · Ver mapa →</span>
    `;

    btn.addEventListener("click", () => selectParty(party.id, true));
    container.appendChild(btn);
  });
}

function renderHeaderDropdown() {
  const container = document.getElementById("partyDropdownBubbles");
  container.innerHTML = "";

  state.data.parties.forEach((party) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `dropdown-bubble-item ${state.selectedPartyId === party.id ? "active" : ""}`;
    btn.style.setProperty("--item-color", party.color);
    btn.innerHTML = `
      <span class="dropdown-bubble-badge">${escapeHtml(party.short_code)}</span>
      <strong>${escapeHtml(party.name)}</strong>
      <small>${party.pages} págs.</small>
    `;
    btn.addEventListener("click", () => {
      container.hidden = true;
      selectParty(party.id, true);
    });
    container.appendChild(btn);
  });
}

function renderMapPartyDock() {
  const dock = document.getElementById("mapPartyDock");
  dock.innerHTML = "";

  state.data.parties.forEach((party) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `dock-party-bubble ${state.selectedPartyId === party.id ? "active" : ""}`;
    btn.style.setProperty("--dock-color", party.color);
    btn.innerHTML = `
      <span class="mini-orb">${escapeHtml(party.short_code)}</span>
      <span>${escapeHtml(party.name)}</span>
    `;
    btn.addEventListener("click", () => {
      if (state.selectedPartyId !== party.id) {
        selectParty(party.id, false);
        renderMapWorkspace();
      }
    });
    dock.appendChild(btn);
  });
}

function renderMapWorkspace() {
  const party = state.data.parties.find((p) => p.id === state.selectedPartyId);
  if (!party) return;

  renderMapPartyDock();
  mindmap.render(party, state.data.domains, state.selectedDomainId);
  renderDomainInspector(party, state.selectedDomainId);
}

function renderDomainInspector(party, domainId) {
  const inspector = document.getElementById("domainInspector");
  const domMeta = state.data.domains.find((d) => d.id === domainId);
  const domData = party.domains[domainId];
  if (!domMeta || !domData) return;

  inspector.innerHTML = `
    <div class="inspector-header">
      <div class="inspector-breadcrumb">
        <span class="inspector-party-chip">${escapeHtml(party.name)}</span>
        <span>·</span>
        <span>${escapeHtml(party.program_title)}</span>
      </div>
      <h2 class="inspector-domain-title">
        <span>${domMeta.icon}</span>
        <span>${escapeHtml(domMeta.label)}</span>
      </h2>
      <p class="inspector-summary">${escapeHtml(domData.overview)}</p>
      <div class="inspector-actions-bar">
        <button type="button" class="inspector-action-btn primary" id="inspectorAskChat">
          ⚖️ Comparar en el chat
        </button>
        <button type="button" class="inspector-action-btn" id="inspectorOpenMatrix">
          📊 Ver 4 partidos
        </button>
      </div>
    </div>

    <div class="inspector-body">
      ${domData.measures
        .map(
          (m, idx) => `
          <article class="measure-card">
            <div class="measure-card-head">
              <h4>${escapeHtml(m.title)}</h4>
              <span class="measure-num">${idx + 1}</span>
            </div>
            <p>${escapeHtml(m.summary)}</p>
            <div class="measure-card-foot">
              <button
                type="button"
                class="citation-chip"
                data-party="${party.id}"
                data-pdf-page="${m.pdf_page}"
                title="Inspeccionar página original del PDF"
              >
                📄 pág. ${escapeHtml(String(m.doc_page))}
              </button>
              <span class="measure-tag">${escapeHtml(m.section)}</span>
            </div>
          </article>
        `
        )
        .join("")}
    </div>
  `;

  inspector.querySelectorAll(".citation-chip").forEach((btn) => {
    btn.addEventListener("click", () => openSourceModal(btn.dataset.party, Number(btn.dataset.pdfPage)));
  });

  inspector.querySelector("#inspectorAskChat").addEventListener("click", () => {
    chatbot.openAndAsk(`¿Qué diferencias hay entre los 4 partidos en ${domMeta.label}?`);
  });

  inspector.querySelector("#inspectorOpenMatrix").addEventListener("click", () => {
    state.compareDomainId = domainId;
    renderCompareView();
    switchView("compare");
  });
}

function renderCompareView() {
  const pillsEl = document.getElementById("compareDomainPills");
  const gridEl = document.getElementById("compareGrid");

  pillsEl.innerHTML = "";
  state.data.domains.forEach((dom) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `compare-domain-pill ${state.compareDomainId === dom.id ? "active" : ""}`;
    btn.innerHTML = `<span>${dom.icon}</span><span>${escapeHtml(dom.label)}</span>`;
    btn.addEventListener("click", () => {
      state.compareDomainId = dom.id;
      renderCompareView();
    });
    pillsEl.appendChild(btn);
  });

  gridEl.innerHTML = "";
  state.data.parties.forEach((party) => {
    const domData = party.domains[state.compareDomainId];
    const col = document.createElement("section");
    col.className = "compare-col";
    col.style.setProperty("--col-color", party.color);
    col.innerHTML = `
      <div class="compare-col-head">
        <div class="compare-col-party">
          <span class="compare-col-dot">${escapeHtml(party.short_code)}</span>
          <div>
            <h3>${escapeHtml(party.name)}</h3>
            <small>${escapeHtml(party.program_title)}</small>
          </div>
        </div>
      </div>
      <p class="compare-col-overview">${escapeHtml(domData.overview)}</p>
      <div class="compare-measure-list">
        ${domData.measures
          .map(
            (m) => `
            <div class="compare-measure-item">
              <strong>${escapeHtml(m.title)}</strong>
              <p>${escapeHtml(m.summary)}</p>
              <button
                type="button"
                class="citation-chip"
                data-party="${party.id}"
                data-pdf-page="${m.pdf_page}"
              >
                📄 pág. ${escapeHtml(String(m.doc_page))}
              </button>
            </div>
          `
          )
          .join("")}
      </div>
    `;

    col.querySelectorAll(".citation-chip").forEach((btn) => {
      btn.addEventListener("click", () => openSourceModal(btn.dataset.party, Number(btn.dataset.pdfPage)));
    });

    gridEl.appendChild(col);
  });
}

async function runPdfSearch(query, partyFilter) {
  const resultsEl = document.getElementById("searchResults");
  if (!query || query.length < 2) {
    resultsEl.innerHTML = `<div class="search-empty-state">Introduce al menos 2 caracteres para buscar en los 4 programas oficiales.</div>`;
    return;
  }

  resultsEl.innerHTML = `<div class="search-empty-state">Buscando en las 395 páginas de los 4 programas electorales…</div>`;

  try {
    const params = new URLSearchParams({ q: query, limit: "16" });
    if (partyFilter) params.set("party", partyFilter);
    const res = await fetch(`/api/search?${params.toString()}`);
    const data = await res.json();

    if (!data.results || data.results.length === 0) {
      resultsEl.innerHTML = `<div class="search-empty-state">No se han encontrado pasajes para «${escapeHtml(query)}».</div>`;
      return;
    }

    const colorMap = Object.fromEntries(state.data.parties.map((p) => [p.id, p.color]));

    resultsEl.innerHTML = data.results
      .map(
        (hit) => `
        <article class="search-hit-card" style="--hit-color:${colorMap[hit.party] || "#0f172a"}">
          <div class="search-hit-meta">
            <div>
              <span class="search-hit-party">${escapeHtml(hit.party_name)}</span>
              <span class="search-hit-section"> · ${escapeHtml(hit.section || "")}</span>
            </div>
            <button
              type="button"
              class="citation-chip"
              data-party="${hit.party}"
              data-pdf-page="${hit.pdf_page}"
            >
              📄 pág. ${hit.doc_page} · Ver página completa
            </button>
          </div>
          <p class="search-hit-text">${escapeHtml(hit.text)}</p>
        </article>
      `
      )
      .join("");

    resultsEl.querySelectorAll(".citation-chip").forEach((btn) => {
      btn.addEventListener("click", () => openSourceModal(btn.dataset.party, Number(btn.dataset.pdfPage)));
    });
  } catch (err) {
    resultsEl.innerHTML = `<div class="search-empty-state">Error al realizar la búsqueda en los documentos.</div>`;
  }
}

async function openSourceModal(partyId, pdfPage) {
  const modal = document.getElementById("sourceModal");
  const party = state.data.parties.find((p) => p.id === partyId);
  if (!party) return;

  const badge = document.getElementById("sourceModalParty");
  badge.textContent = party.name;
  badge.style.background = party.color;

  document.getElementById("sourceModalTitle").textContent = party.program_title;
  document.getElementById("sourceModalMeta").textContent = "Cargando texto oficial del PDF…";
  document.getElementById("sourceModalBody").textContent = "";
  const pdfLink = document.getElementById("sourceModalPdfLink");
  pdfLink.href = `/api/pdf/${partyId}#page=${pdfPage}`;
  pdfLink.hidden = false;
  modal.hidden = false;

  try {
    const res = await fetch(`/api/page/${partyId}/${pdfPage}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const page = await res.json();
    pdfLink.hidden = page.has_pdf === false;
    document.getElementById("sourceModalMeta").textContent =
      `Archivo: ${party.pdf_filename} · Página impresa: ${page.doc_page} (PDF pág. ${page.pdf_page}) · Sección: ${page.section}`;
    document.getElementById("sourceModalBody").textContent =
      page.text || "Página sin contenido textual extraíble.";
  } catch {
    document.getElementById("sourceModalMeta").textContent = `Archivo: ${party.pdf_filename} · PDF pág. ${pdfPage}`;
    document.getElementById("sourceModalBody").textContent =
      "No se pudo cargar la vista previa de texto. Puedes abrir el PDF oficial directamente con el botón inferior.";
  }
}

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

init();
