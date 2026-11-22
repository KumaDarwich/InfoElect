#!/usr/bin/env python3
"""
Extracts and indexes all 4 downloaded 29N 2026 Spanish electoral program PDFs
into clean, page-attributed, section-aware semantic chunks for InfoElect's
impartial RAG comparator and source viewer.
"""

import json
import os
import re
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = BASE_DIR / "pdfs"
DATA_DIR = BASE_DIR / "data"

PARTIES = {
    "frente_amplio": {
        "name": "Frente Amplio",
        "pdf": PDF_DIR / "frente_amplio.pdf",
        "filename": "ProgramaFrenteAmplio.pdf",
        "title": "Un programa como una casa",
        "toc_max_pdf_page": 6,
    },
    "pp": {
        "name": "PP",
        "pdf": PDF_DIR / "pp.pdf",
        "filename": "PROGRAMA-ELECTORAL-PP-2026-RECONSTRUCCION-NACIONAL.pdf",
        "title": "Reconstrucción Nacional",
        "toc_max_pdf_page": 7,
    },
    "psoe": {
        "name": "PSOE",
        "pdf": PDF_DIR / "psoe.pdf",
        "filename": "PROGRAMAPSOE29N26.pdf",
        "title": "La fuerza de seguir avanzando",
        "toc_max_pdf_page": 5,
    },
    "vox": {
        "name": "VOX",
        "pdf": PDF_DIR / "vox.pdf",
        "filename": "Programa-completo-A5-1.pdf",
        "title": "Es Sentido Común",
        "toc_max_pdf_page": 6,
    },
}

RUNNING_HEADERS = {
    "ES SENTIDO COMÚN",
    "PROGRAMA ELECTORAL FRENTE AMPLIO",
    "PROGRAMA ELECTORAL",
    "LA FUERZA DE SEGUIR AVANZANDO.",
    "RECONSTRUCCIÓN NACIONAL",
    "EL PROGRAMA DEL CAMBIO NECESARIO PARA ESPAÑA",
    "VOTA",
}


def extract_pdf_pages(pdf_path: Path) -> list[str]:
    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    pages = result.stdout.split("\f")
    # pdftotext usually leaves a trailing empty string after final form feed
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def detect_doc_page(lines: list[str], pdf_page: int) -> tuple[int, list[str]]:
    cleaned = list(lines)
    doc_page = pdf_page
    if cleaned and re.fullmatch(r"\d{1,3}", cleaned[0].strip()):
        val = int(cleaned[0].strip())
        if abs(val - pdf_page) <= 35:
            doc_page = val
            cleaned = cleaned[1:]
    if cleaned and re.fullmatch(r"\d{1,3}", cleaned[-1].strip()):
        val = int(cleaned[-1].strip())
        if abs(val - pdf_page) <= 35:
            doc_page = val
            cleaned = cleaned[:-1]
    return doc_page, cleaned


def clean_page_text(raw: str, pdf_page: int, party_id: str) -> tuple[int, str, str]:
    lines = [l.rstrip() for l in raw.splitlines()]
    non_empty = [l.strip() for l in lines if l.strip()]
    if not non_empty:
        return pdf_page, "", ""

    doc_page, body_lines = detect_doc_page(non_empty, pdf_page)

    filtered = []
    detected_heading = ""
    for line in body_lines:
        upper = line.upper().strip()
        if upper in RUNNING_HEADERS:
            continue
        # Detect uppercase chapter/section headers or numbered section headers
        if not detected_heading:
            if party_id == "frente_amplio" and re.match(r"^\d+\.\d+\.\s+\S", line):
                detected_heading = line
            elif party_id == "pp" and re.match(r"^\d+\.\d+\s+[A-ZÁÉÍÓÚÑ]", line):
                detected_heading = line
            elif party_id == "vox" and len(line) > 5 and line.isupper() and not line.startswith("•"):
                detected_heading = line.title()
            elif party_id == "psoe" and len(line) < 95 and not re.match(r"^\d+\.", line) and not line.endswith(".") and line[0].isupper():
                if len(line.split()) >= 2:
                    detected_heading = line
        filtered.append(line)

    # Reconstruct text while preserving paragraph/bullet breaks and fixing hyphenation
    text = "\n".join(filtered)
    # Fix soft hyphen line breaks (word-\ncontinuation -> wordcontinuation)
    text = re.sub(r"([a-záéíóúñü])-\n([a-záéíóúñü])", r"\1\2", text)
    return doc_page, text, detected_heading


def is_toc_or_cover(text: str, pdf_page: int, toc_max: int) -> bool:
    if pdf_page <= toc_max:
        return True
    if text.count("....") >= 3:
        return True
    if len(text.strip()) < 60:
        return True
    return False


def split_into_semantic_chunks(text: str, party_id: str) -> list[str]:
    """
    Re-joins wrapped PDF lines into logical paragraphs/commitments, then groups
    short consecutive items or splits overly long paragraphs into ~220-750 char chunks.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    paragraphs: list[str] = []
    buf: list[str] = []

    def flush():
        if buf:
            joined = " ".join(buf)
            joined = re.sub(r"\s+", " ", joined).strip()
            joined = re.sub(r"^[●•■▪\-]\s*", "", joined).strip()
            if len(joined) >= 35:
                paragraphs.append(joined)
            buf.clear()

    for line in lines:
        # Standalone bullet character -> starts a new item
        if line in {"●", "•", "■", "▪", "-", "–", "‘‘", "’’"}:
            flush()
            continue
        # Standalone numbered item marker like "7." or "108" starts a new item
        if re.fullmatch(r"\d{1,3}\.?", line):
            flush()
            buf.append(line if line.endswith(".") else line + ".")
            continue
        # Starts with bullet or numbered commitment (e.g. "100. ", "48. ", "108 GARANTIZAREMOS")
        is_new_item = bool(
            re.match(r"^[●•■▪]\s+", line)
            or re.match(r"^\d{1,3}\.\s+[A-ZÁÉÍÓÚÑ]", line)
            or (party_id == "pp" and re.match(r"^\d{1,3}\s+[A-ZÁÉÍÓÚÑ]{3,}", line))
            or re.match(r"^\d+\.\d+\.?\s+[A-ZÁÉÍÓÚÑ]", line)
        )
        if is_new_item:
            flush()
            buf.append(line)
        else:
            # Check if previous buffer ended a sentence and this line looks like a new heading/paragraph
            if buf and buf[-1].endswith((".", ":", "?", "!")) and len(" ".join(buf)) > 260 and line[0].isupper():
                flush()
            buf.append(line)
    flush()

    # Normalize chunk sizes: split >850 char paragraphs on sentence boundaries
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= 850:
            chunks.append(para)
        else:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            cur = ""
            for s in sentences:
                if len(cur) + len(s) + 1 > 750 and cur:
                    chunks.append(cur.strip())
                    cur = s
                else:
                    cur = (cur + " " + s).strip()
            if len(cur.strip()) >= 35:
                chunks.append(cur.strip())
    return chunks


def build_all():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks = []
    pages_store = {}
    stats = {}

    for party_id, cfg in PARTIES.items():
        pdf_path = cfg["pdf"]
        if not pdf_path.exists():
            raise FileNotFoundError(f"Missing PDF: {pdf_path}")

        raw_pages = extract_pdf_pages(pdf_path)
        pages_store[party_id] = []
        current_section = cfg["title"]
        party_chunk_count = 0

        for idx, raw in enumerate(raw_pages, 1):
            doc_page, clean_txt, heading = clean_page_text(raw, idx, party_id)
            if heading and len(heading) <= 110:
                current_section = heading

            pages_store[party_id].append(
                {
                    "pdf_page": idx,
                    "doc_page": doc_page,
                    "section": current_section,
                    "text": clean_txt,
                }
            )

            if is_toc_or_cover(clean_txt, idx, cfg["toc_max_pdf_page"]):
                continue

            chunks = split_into_semantic_chunks(clean_txt, party_id)
            for c_idx, ch in enumerate(chunks):
                all_chunks.append(
                    {
                        "id": f"{party_id}_p{idx}_{c_idx}",
                        "party": party_id,
                        "party_name": cfg["name"],
                        "pdf_page": idx,
                        "doc_page": doc_page,
                        "section": current_section,
                        "text": ch,
                    }
                )
                party_chunk_count += 1

        stats[party_id] = {
            "total_pdf_pages": len(raw_pages),
            "indexed_chunks": party_chunk_count,
        }

    with open(DATA_DIR / "corpus_chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=None)

    with open(DATA_DIR / "pages_text.json", "w", encoding="utf-8") as f:
        json.dump(pages_store, f, ensure_ascii=False, indent=None)

    print("Indexed InfoElect corpus successfully:")
    for pid, s in stats.items():
        print(f"  - {pid}: {s['total_pdf_pages']} PDF pages -> {s['indexed_chunks']} semantic chunks")
    print(f"Total indexed chunks: {len(all_chunks)}")


if __name__ == "__main__":
    build_all()
