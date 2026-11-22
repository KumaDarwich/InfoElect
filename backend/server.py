#!/usr/bin/env python3
"""
InfoElect FastAPI Backend Server.
Serves the interactive visual map dataset, impartial comparative RAG chatbot,
full-text search across all 4 official 29N 2026 PDFs, source page inspection,
and the static frontend application.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rag_engine import ImpartialComparatorEngine, PARTY_ORDER

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = BASE_DIR / "pdfs"
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="InfoElect API",
    description="Explorador visual y comparador imparcial de programas electorales 29N 2026",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = ImpartialComparatorEngine()


def load_programs_data() -> dict:
    path = DATA_DIR / "programs_data.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="Dataset de programas aún no inicializado.")
    return json.loads(path.read_text(encoding="utf-8"))


class ChatRequest(BaseModel):
    message: str
    parties: Optional[list[str]] = None


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "indexed_chunks": len(engine.chunks),
        "curated_topics": len(engine.topics),
        "parties": PARTY_ORDER,
    }


@app.get("/api/programs")
def get_programs():
    return JSONResponse(content=load_programs_data())


@app.post("/api/chat")
def chat_compare(req: ChatRequest):
    result = engine.answer_question(req.message, ui_parties=req.parties)
    return JSONResponse(content=result)


@app.get("/api/search")
def search_programs(
    q: str = Query(..., min_length=2),
    party: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=30),
):
    hits = engine.search_raw(q, party=party, limit=limit)
    return {"query": q, "party": party, "count": len(hits), "results": hits}


@app.get("/api/page/{party_id}/{pdf_page}")
def get_source_page(party_id: str, pdf_page: int):
    if party_id not in PARTY_ORDER:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    page = engine.get_page(party_id, pdf_page)
    if not page:
        raise HTTPException(status_code=404, detail="Página no encontrada.")
    has_pdf = (PDF_DIR / f"{party_id}.pdf").resolve().exists()
    return {
        "party": party_id,
        "has_pdf": has_pdf,
        "pdf_url": f"/api/pdf/{party_id}#page={pdf_page}" if has_pdf else None,
        **page,
    }


@app.get("/api/pdf/{party_id}")
def serve_pdf(party_id: str):
    if party_id not in PARTY_ORDER:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    pdf_path = (PDF_DIR / f"{party_id}.pdf").resolve()
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado.")
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{party_id}_29N2026.pdf"'},
    )


# Mount frontend assets and root index
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/")
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend no encontrado.")
    return FileResponse(index_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
