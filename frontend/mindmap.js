/**
 * InfoElect Interactive Radial Mind-Map Renderer
 * Renders a smooth, zoomable, pannable visual concept map connecting the
 * selected party hub to all 8 core policy domains with Bézier paths.
 */

const STAGE_W = 960;
const STAGE_H = 680;
const CENTER_X = 480;
const CENTER_Y = 340;

// 8 balanced radial coordinates around (480, 340) in a 960x680 coordinate space
// Carefully spaced so 198px-wide domain bubbles never overlap at any screen size
const DOMAIN_COORDS = [
  { x: 205, y: 120 }, // 0: Top-left (Economía)
  { x: 480, y: 82 },  // 1: Top-center (Vivienda)
  { x: 755, y: 120 }, // 2: Top-right (Sanidad)
  { x: 810, y: 340 }, // 3: Mid-right (Educación)
  { x: 755, y: 560 }, // 4: Bottom-right (Inmigración)
  { x: 480, y: 598 }, // 5: Bottom-center (Empleo y Pensiones)
  { x: 205, y: 560 }, // 6: Bottom-left (Seguridad y Justicia)
  { x: 150, y: 340 }, // 7: Mid-left (Energía, Familia y Rural)
];

export class VisualMindMap {
  constructor({ viewportEl, stageEl, svgEl, nodesEl, onSelectDomain }) {
    this.viewportEl = viewportEl;
    this.stageEl = stageEl;
    this.svgEl = svgEl;
    this.nodesEl = nodesEl;
    this.onSelectDomain = onSelectDomain;

    this.scale = 1;
    this.baseScale = 1;
    this.panX = 0;
    this.panY = 0;
    this.isDragging = false;
    this.dragStart = { x: 0, y: 0 };

    this.party = null;
    this.domainsMeta = [];
    this.activeDomainId = null;

    this._bindInteractions();
    this._bindResize();
  }

  _bindInteractions() {
    this.viewportEl.addEventListener("pointerdown", (e) => {
      if (e.target.closest("button, a")) return;
      this.isDragging = true;
      this.viewportEl.classList.add("dragging");
      this.dragStart = { x: e.clientX - this.panX, y: e.clientY - this.panY };
      this.viewportEl.setPointerCapture(e.pointerId);
    });

    this.viewportEl.addEventListener("pointermove", (e) => {
      if (!this.isDragging) return;
      this.panX = e.clientX - this.dragStart.x;
      this.panY = e.clientY - this.dragStart.y;
      this._applyTransform();
    });

    const endDrag = () => {
      this.isDragging = false;
      this.viewportEl.classList.remove("dragging");
    };
    this.viewportEl.addEventListener("pointerup", endDrag);
    this.viewportEl.addEventListener("pointercancel", endDrag);

    this.viewportEl.addEventListener(
      "wheel",
      (e) => {
        if (!e.ctrlKey && !e.metaKey) return;
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        this.zoomBy(delta);
      },
      { passive: false }
    );
  }

  _bindResize() {
    if (typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(() => this.fitToViewport(false));
      ro.observe(this.viewportEl);
    }
    window.addEventListener("resize", () => this.fitToViewport(false));
  }

  fitToViewport(resetPan = true) {
    const rect = this.viewportEl.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const padX = 36;
    const padY = 92; // account for top party dock & bottom hint
    const sx = (rect.width - padX) / STAGE_W;
    const sy = (rect.height - padY) / STAGE_H;
    this.baseScale = Math.max(0.45, Math.min(1.06, Math.min(sx, sy)));
    this.scale = this.baseScale;
    if (resetPan) {
      this.panX = 0;
      this.panY = 8;
    }
    this._applyTransform();
  }

  zoomBy(delta) {
    this.scale = Math.max(0.45, Math.min(1.65, this.scale + delta));
    this._applyTransform();
  }

  resetView() {
    this.fitToViewport(true);
  }

  _applyTransform() {
    this.stageEl.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.scale})`;
  }

  render(party, domainsMeta, activeDomainId) {
    this.party = party;
    this.domainsMeta = domainsMeta;
    this.activeDomainId = activeDomainId;

    this.svgEl.innerHTML = "";
    this.nodesEl.innerHTML = "";

    // Decorative subtle orbit ellipse
    const orbit = document.createElementNS("http://www.w3.org/2000/svg", "ellipse");
    orbit.setAttribute("cx", String(CENTER_X));
    orbit.setAttribute("cy", String(CENTER_Y));
    orbit.setAttribute("rx", "318");
    orbit.setAttribute("ry", "248");
    orbit.setAttribute("fill", "none");
    orbit.setAttribute("stroke", "rgba(15, 23, 42, 0.06)");
    orbit.setAttribute("stroke-width", "1.5");
    orbit.setAttribute("stroke-dasharray", "4 7");
    this.svgEl.appendChild(orbit);

    // Draw edges + domain nodes
    domainsMeta.forEach((dom, idx) => {
      const pos = DOMAIN_COORDS[idx % DOMAIN_COORDS.length];
      const domainData = party.domains[dom.id];
      const isActive = dom.id === activeDomainId;

      // Smooth cubic Bézier curve from center hub to domain bubble
      const dx = pos.x - CENTER_X;
      const dy = pos.y - CENTER_Y;
      const c1x = CENTER_X + dx * 0.42;
      const c1y = CENTER_Y + dy * 0.14;
      const c2x = CENTER_X + dx * 0.65;
      const c2y = CENTER_Y + dy * 0.86;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", `M ${CENTER_X} ${CENTER_Y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${pos.x} ${pos.y}`);
      path.setAttribute("class", `mindmap-edge ${isActive ? "active" : ""}`);
      path.dataset.domain = dom.id;
      this.svgEl.appendChild(path);

      // Endpoint dot near domain node
      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("cx", String(CENTER_X + dx * 0.62));
      dot.setAttribute("cy", String(CENTER_Y + dy * 0.62));
      dot.setAttribute("r", isActive ? "4.5" : "3");
      dot.setAttribute("fill", isActive ? party.color : "rgba(15, 23, 42, 0.18)");
      this.svgEl.appendChild(dot);

      // Domain bubble HTML node
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `map-domain-node ${isActive ? "active" : ""}`;
      btn.style.left = `${pos.x}px`;
      btn.style.top = `${pos.y}px`;
      btn.dataset.domain = dom.id;
      btn.setAttribute("aria-pressed", String(isActive));

      const firstTitle = domainData?.measures?.[0]?.title || "";
      const measureCount = domainData?.measures?.length || 0;

      btn.innerHTML = `
        <div class="domain-node-top">
          <span class="domain-node-icon" aria-hidden="true">${dom.icon}</span>
          <span class="domain-node-count">${measureCount} medidas</span>
        </div>
        <div class="domain-node-title">${dom.short_label}</div>
        <div class="domain-node-teaser">${this._escape(firstTitle)}</div>
      `;

      btn.addEventListener("mouseenter", () => this._highlightEdge(dom.id, true));
      btn.addEventListener("mouseleave", () => this._highlightEdge(dom.id, false));
      btn.addEventListener("click", () => {
        if (this.onSelectDomain) this.onSelectDomain(dom.id);
      });

      this.nodesEl.appendChild(btn);
    });

    // Center Party Hub Node
    const center = document.createElement("div");
    center.className = "map-center-node";
    center.innerHTML = `
      <div class="center-node-badge">${this._escape(party.short_code)}</div>
      <div class="center-node-title">${this._escape(party.name)}</div>
      <div class="center-node-slogan">«${this._escape(party.program_title)}»</div>
      <a class="center-node-pdf" href="/api/pdf/${party.id}" target="_blank" rel="noopener">
        PDF (${party.pages} págs.) ↗
      </a>
    `;
    this.nodesEl.appendChild(center);

    requestAnimationFrame(() => this.fitToViewport(false));
  }

  _highlightEdge(domainId, hovered) {
    const edges = this.svgEl.querySelectorAll(".mindmap-edge");
    edges.forEach((edge) => {
      const isTarget = edge.dataset.domain === domainId;
      const isSelected = edge.dataset.domain === this.activeDomainId;
      if (hovered) {
        edge.classList.toggle("dimmed", !isTarget && !isSelected);
        if (isTarget) edge.style.stroke = this.party.color;
      } else {
        edge.classList.remove("dimmed");
        edge.style.stroke = "";
      }
    });
  }

  _escape(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
}
