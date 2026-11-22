#!/usr/bin/env python3
"""
InfoElect Impartial Comparative RAG Engine.
Strictly neutral, source-attributed comparison engine grounded exclusively in the
4 downloaded 29N 2026 Spanish electoral program PDFs.
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

PARTY_ORDER = ["frente_amplio", "pp", "psoe", "vox"]

PARTY_META = {
    "frente_amplio": {
        "id": "frente_amplio",
        "name": "Frente Amplio",
        "program_title": "Un programa como una casa",
        "color": "#EA4C1D",
    },
    "pp": {
        "id": "pp",
        "name": "PP",
        "program_title": "Reconstrucción Nacional",
        "color": "#0056A3",
    },
    "psoe": {
        "id": "psoe",
        "name": "PSOE",
        "program_title": "La fuerza de seguir avanzando",
        "color": "#E30613",
    },
    "vox": {
        "id": "vox",
        "name": "VOX",
        "program_title": "Es Sentido Común",
        "color": "#5BB318",
    },
}

SPANISH_STOPWORDS = {
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "asi", "aun",
    "bajo", "bien", "cada", "casi", "como", "con", "contra", "cual", "cuales",
    "cuando", "cuanto", "de", "del", "desde", "diferencia", "diferencias",
    "donde", "dos", "el", "ella", "ellas", "ellos", "en", "entre", "era",
    "es", "esa", "esas", "ese", "eso", "esos", "esta", "estaba", "estado",
    "estan", "estar", "estas", "este", "esto", "estos", "fue", "ha", "haber",
    "habia", "hace", "hacen", "hacer", "hacia", "han", "hasta", "hay", "he",
    "infoelect", "la", "las", "le", "les", "lo", "los", "mas", "me", "medida",
    "medidas", "mi", "mis", "mucho", "muy", "nada", "ni", "no", "nos",
    "nosotros", "nuestra", "nuestro", "o", "opinion", "otra", "otras", "otro",
    "otros", "para", "partido", "partidos", "pero", "poco", "poder", "politica",
    "politicas", "por", "porque", "programa", "programas", "propone", "proponen",
    "propuesta", "propuestas", "puede", "pueden", "que", "quien", "quienes",
    "respecto", "se", "sea", "segun", "ser", "sera", "si", "sido", "siempre",
    "sin", "sobre", "solo", "son", "su", "sus", "tambien", "tan", "tanto",
    "te", "tema", "tendran", "tener", "tiene", "tienen", "toda", "todas",
    "todo", "todos", "tu", "un", "una", "unas", "uno", "unos", "va", "van",
    "ver", "y", "ya", "yo", "compara", "comparar", "comparativa", "comparame",
    "dime", "explica", "explicame", "habla", "hablan", "dicen", "dice",
    "frente", "amplio", "pp", "psoe", "vox", "popular", "socialista",
    "cuatro", "principales", "espana", "espanoles", "espanola",
    "debo", "deberia", "quiero", "saber", "puedo", "ayudame", "producto",
    "productos", "cosa", "cosas", "temas", "ambito", "ambitos", "elecciones",
    "candidato", "candidatos", "opcion", "opciones",
}

SYNONYM_GROUPS = [
    {"pension", "pensiones", "jubilacion", "pensionista", "pensionistas", "cotizacion", "cotizaciones", "ipc", "revalorizacion"},
    {"vivienda", "viviendas", "alquiler", "alquileres", "hipoteca", "hipotecas", "inmueble", "piso", "pisos", "desahucio", "desahucios", "okupacion", "ocupacion", "inquiokupacion", "inquiocupacion"},
    {"impuesto", "impuestos", "fiscal", "fiscalidad", "tributario", "tributos", "irpf", "iva", "sociedades", "patrimonio", "sucesiones", "hacienda"},
    {"sanidad", "salud", "hospital", "hospitales", "medico", "medicos", "sanitario", "sanitarios", "primaria", "espera", "mental", "bucodental", "farmacia"},
    {"celiaquia", "celiaco", "celiaca", "celiacos", "celiacas", "gluten"},
    {"educacion", "educativo", "colegio", "colegios", "escuela", "escuelas", "universidad", "universidades", "beca", "becas", "profesor", "profesorado", "docente", "pisa", "ebau", "pau", "evau", "concertada", "fp"},
    {"inmigracion", "inmigrante", "inmigrantes", "migracion", "migraciones", "migrante", "migrantes", "frontera", "fronteras", "regularizacion", "expulsion", "deportacion", "asilo", "extranjeria", "ceuta", "melilla", "cie"},
    {"empleo", "trabajo", "laboral", "salario", "salarios", "sueldo", "sueldos", "smi", "jornada", "horas", "despido", "paro", "desempleo", "contrato", "contratos"},
    {"autonomo", "autonomos", "pyme", "pymes", "emprendedor", "emprendedores", "empresa", "empresas"},
    {"energia", "energetico", "energetica", "electricidad", "electrica", "luz", "nuclear", "nucleares", "renovable", "renovables", "climatico", "clima", "ecologica"},
    {"agricultura", "ganaderia", "pesca", "campo", "rural", "agricultores", "ganaderos", "pac", "agua", "regadio", "hidrologico", "despoblacion"},
    {"familia", "familias", "natalidad", "hijos", "crianza", "maternidad", "paternidad", "conciliacion", "cuidados", "dependencia", "infancia"},
    {"justicia", "judicial", "jueces", "fiscales", "cgpj", "corrupcion", "tribunal", "seguridad", "policia", "guardia", "delincuencia", "multirreincidencia", "defensa", "ejercito", "otan"},
    {"autonomia", "autonomias", "autonomica", "financiacion", "territorial", "constitucion", "republica", "monarquia", "centralizacion", "competencias"},
    {"transporte", "tren", "trenes", "cercanias", "ferrocarril", "renfe", "adif", "infraestructuras", "carreteras", "movilidad"},
    {"digital", "digitalizacion", "inteligencia", "artificial", "ia", "algoritmo", "pantallas", "redes", "menores"},
]

PARTY_ALIASES = {
    "frente_amplio": [r"\bfrente\s+amplio\b", r"\bfrente\b"],
    "pp": [r"\bpp\b", r"\bpartido\s+popular\b", r"\bpopulares\b", r"\bfeij[oó]o\b"],
    "psoe": [r"\bpsoe\b", r"\bsocialistas?\b", r"\bs[aá]nchez\b"],
    "vox": [r"\bvox\b", r"\babascal\b"],
}

OPINION_PATTERNS = [
    r"\b(mejor|peor|mejores|peores)\s+(partido|programa|opci[oó]n|candidato|propuesta|medida)",
    r"\bqu[eé]\s+partido\s+(es\s+mejor|es\s+peor|me\s+conviene|deber[ií]a|voto|recomiendas)",
    r"\ba\s+qui[eé]n\s+(voto|votar|debo\s+votar|deber[ií]a\s+votar|me\s+recomiendas)",
    r"\b(tu\s+opini[oó]n|qu[eé]\s+opinas|qu[eé]\s+piensas|mojate|m[oó]jate|elige\s+uno|posici[oó]nate)",
    r"\b(qui[eé]n\s+tiene\s+raz[oó]n|qui[eé]n\s+miente|qui[eé]n\s+lo\s+hace\s+mejor|puntuaci[oó]n|ranking|nota\s+a\s+cada)",
    r"\bcu[aá]l\s+(es\s+mejor|es\s+el\s+mejor|me\s+recomiendas|prefieres|gana)",
]

GREETING_PATTERNS = [
    r"^(hola|buenas|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches|hey|saludos|qu[eé]\s+tal|ayuda|help)[\s!?.,]*$"
]


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def light_stem_es(word: str) -> str:
    """Gentle, safe Spanish normalizer that preserves distinct roots (e.g. pension vs suspension)."""
    w = word
    if len(w) <= 4:
        return w
    for suffix in (
        "aciones", "iciones", "amiento", "imiento", "idades", "adores",
        "adoras", "istas", "ismos", "mente", "acion", "icion", "idad",
        "ales", "ares", "ores", "oras", "ivos", "ivas", "icos", "icas",
        "bles", "es", "s",
    ):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[: -len(suffix)]
    return w


def tokenize(text: str, remove_stop: bool = True) -> list[str]:
    clean = strip_accents(text.lower())
    raw_tokens = re.findall(r"[a-z0-9]+", clean)
    out = []
    for tok in raw_tokens:
        if len(tok) <= 1 and tok not in {"y", "o"}:
            continue
        if remove_stop and tok in SPANISH_STOPWORDS:
            continue
        out.append(light_stem_es(tok))
    return out


def expand_query_tokens(raw_query: str) -> tuple[list[str], set[str]]:
    clean = strip_accents(raw_query.lower())
    raw_words = [w for w in re.findall(r"[a-z0-9]+", clean) if len(w) > 1 and w not in SPANISH_STOPWORDS]
    primary_stems = [light_stem_es(w) for w in raw_words]
    expanded_stems: set[str] = set()
    for w in raw_words:
        for grp in SYNONYM_GROUPS:
            if w in grp:
                for syn in grp:
                    st = light_stem_es(syn)
                    if st not in primary_stems:
                        expanded_stems.add(st)
    return primary_stems, expanded_stems


class ImpartialComparatorEngine:
    def __init__(self) -> None:
        self.chunks: list[dict[str, Any]] = []
        self.topics: list[dict[str, Any]] = []
        self.pages_text: dict[str, list[dict[str, Any]]] = {}

        # Per-party BM25 structures
        self.party_chunks: dict[str, list[int]] = defaultdict(list)
        self.doc_tokens: list[Counter[str]] = []
        self.doc_len: list[int] = []
        self.avg_doc_len: dict[str, float] = {}
        self.df: dict[str, Counter[str]] = defaultdict(Counter)
        self.inv_index: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))

        self._load_data()

    def _load_data(self) -> None:
        chunks_path = DATA_DIR / "corpus_chunks.json"
        if chunks_path.exists():
            self.chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

        topics_path = DATA_DIR / "topics_knowledge.json"
        if topics_path.exists():
            self.topics = json.loads(topics_path.read_text(encoding="utf-8"))

        pages_path = DATA_DIR / "pages_text.json"
        if pages_path.exists():
            self.pages_text = json.loads(pages_path.read_text(encoding="utf-8"))

        # Build per-party BM25 index
        for idx, ch in enumerate(self.chunks):
            pid = ch["party"]
            self.party_chunks[pid].append(idx)
            # Weight section heading terms lightly alongside chunk text
            combined = f"{ch.get('section', '')} {ch.get('text', '')}"
            toks = tokenize(combined, remove_stop=True)
            counts = Counter(toks)
            self.doc_tokens.append(counts)
            self.doc_len.append(len(toks))
            for tok in counts:
                self.df[pid][tok] += 1
                self.inv_index[pid][tok].append(idx)

        for pid, indices in self.party_chunks.items():
            total_len = sum(self.doc_len[i] for i in indices)
            self.avg_doc_len[pid] = total_len / max(len(indices), 1)

    def detect_parties(self, query: str, ui_parties: list[str] | None = None) -> list[str]:
        found = []
        q_low = query.lower()
        for pid in PARTY_ORDER:
            for pat in PARTY_ALIASES[pid]:
                if re.search(pat, q_low, re.IGNORECASE):
                    if pid not in found:
                        found.append(pid)
                    break
        if found:
            return found
        if ui_parties:
            valid = [p for p in PARTY_ORDER if p in ui_parties]
            if valid:
                return valid
        return list(PARTY_ORDER)

    def is_opinion_prompt(self, query: str) -> bool:
        q = query.lower().strip()
        return any(re.search(pat, q, re.IGNORECASE) for pat in OPINION_PATTERNS)

    def is_greeting(self, query: str) -> bool:
        q = query.lower().strip()
        return any(re.match(pat, q, re.IGNORECASE) for pat in GREETING_PATTERNS)

    def match_curated_topic(self, query: str) -> tuple[dict[str, Any] | None, float]:
        """Match query against curated verified policy topics if strongly aligned."""
        q_clean = strip_accents(query.lower())
        q_words = set(re.findall(r"[a-z0-9]+", q_clean))
        q_stems = set(tokenize(query, remove_stop=True))

        # If query has specific narrow terms NOT in a topic's core scope, we may still show live BM25
        best_topic = None
        best_score = 0.0

        for topic in self.topics:
            score = 0.0
            for kw in topic.get("exact_triggers", []):
                kw_clean = strip_accents(kw.lower())
                if re.search(r"\b" + re.escape(kw_clean) + r"\b", q_clean):
                    score += 3.0 if " " in kw_clean else 2.2
            for kw in topic.get("keywords", []):
                kw_stem = light_stem_es(strip_accents(kw.lower()))
                if kw_stem in q_stems or strip_accents(kw.lower()) in q_words:
                    score += 1.0
            if score > best_score:
                best_score = score
                best_topic = topic

        # Require a confident match
        if best_topic and best_score >= 2.0:
            # Penalize if user asked a very specific sub-question not covered by generic topic keywords
            return best_topic, best_score
        return None, 0.0

    def search_party_bm25(
        self,
        party_id: str,
        primary_stems: list[str],
        expanded_stems: set[str],
        raw_query: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """BM25 search within a single party's full PDF corpus."""
        n_docs = len(self.party_chunks.get(party_id, []))
        if n_docs == 0 or (not primary_stems and not expanded_stems):
            return []

        avgdl = self.avg_doc_len.get(party_id, 60.0)
        k1 = 1.4
        b = 0.72

        candidate_scores: dict[int, float] = defaultdict(float)
        primary_hits: dict[int, set[str]] = defaultdict(set)

        all_query_terms: list[tuple[str, float, bool]] = []
        seen = set()
        for t in primary_stems:
            if t not in seen:
                all_query_terms.append((t, 1.0, True))
                seen.add(t)
        for t in expanded_stems:
            if t not in seen:
                all_query_terms.append((t, 0.38, False))
                seen.add(t)

        for term, weight, is_primary in all_query_terms:
            postings = self.inv_index[party_id].get(term)
            if not postings:
                continue
            df = self.df[party_id][term]
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            for doc_idx in postings:
                tf = self.doc_tokens[doc_idx][term]
                dl = self.doc_len[doc_idx]
                bm25 = idf * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * dl / avgdl)))
                candidate_scores[doc_idx] += bm25 * weight
                if is_primary:
                    primary_hits[doc_idx].add(term)

        if not candidate_scores:
            return []

        # Boost exact phrase matches and multi-term coverage
        q_clean = strip_accents(raw_query.lower())
        key_phrases = [p for p in re.findall(r"[a-z0-9]+(?:\s+[a-z0-9]+)?", q_clean) if len(p) >= 6]
        ranked = []
        for doc_idx, base_score in candidate_scores.items():
            ch = self.chunks[doc_idx]
            txt_clean = strip_accents(ch["text"].lower())
            coverage = len(primary_hits[doc_idx])
            score = base_score * (1.0 + 0.35 * coverage)

            # Bonus if section title itself mentions primary query terms
            sec_stems = set(tokenize(ch.get("section", ""), remove_stop=True))
            if sec_stems & set(primary_stems):
                score *= 1.25

            # Small phrase boost
            for ph in key_phrases[:4]:
                if ph in txt_clean and not any(w in SPANISH_STOPWORDS for w in ph.split()):
                    score *= 1.15
                    break

            # Require either a primary stem hit OR strong synonym score
            if coverage == 0 and score < 2.2:
                continue
            if score < 1.25:
                continue
            ranked.append((score, doc_idx))

        ranked.sort(key=lambda x: x[0], reverse=True)

        # Deduplicate near-identical pages when picking top_k so results span distinct measures
        selected = []
        seen_ids = set()
        for score, doc_idx in ranked:
            if doc_idx in seen_ids:
                continue
            ch = self.chunks[doc_idx]
            selected.append(
                {
                    "id": ch["id"],
                    "party": ch["party"],
                    "party_name": ch["party_name"],
                    "pdf_page": ch["pdf_page"],
                    "doc_page": ch["doc_page"],
                    "section": ch["section"],
                    "text": ch["text"],
                    "score": round(score, 2),
                }
            )
            seen_ids.add(doc_idx)
            if len(selected) >= top_k:
                break
        return selected

    def summarize_snippet(self, text: str, max_len: int = 340, focus_terms: list[str] | None = None) -> str:
        t = re.sub(r"\s+", " ", text).strip()
        if len(t) <= max_len:
            return t
        # If focus_terms appear later in the chunk, window around the sentence containing them
        if focus_terms:
            t_low = strip_accents(t.lower())
            best_pos = -1
            for term in focus_terms:
                pos = t_low.find(term)
                if pos != -1 and (best_pos == -1 or pos < best_pos):
                    best_pos = pos
            if best_pos > max_len * 0.6:
                start = max(0, best_pos - 90)
                # Snap to sentence or word boundary
                sent_break = t.rfind(". ", 0, start + 30)
                if sent_break != -1 and best_pos - sent_break < max_len * 0.7:
                    start = sent_break + 2
                else:
                    ws = t.find(" ", start)
                    if ws != -1 and ws < best_pos:
                        start = ws + 1
                sub = t[start : start + max_len]
                prefix = "…" if start > 0 else ""
                suffix = "…" if start + max_len < len(t) else ""
                return (prefix + sub.rsplit(" ", 1)[0].strip() + suffix) if suffix else (prefix + sub.strip())
        cut = t[:max_len]
        last_period = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(": "))
        if last_period > max_len * 0.55:
            return cut[: last_period + 1].strip()
        return cut.rsplit(" ", 1)[0].strip() + "…"

    def answer_question(
        self,
        query: str,
        ui_parties: list[str] | None = None,
    ) -> dict[str, Any]:
        q = (query or "").strip()
        if not q:
            return {
                "mode": "info",
                "impartial_notice": None,
                "intro": "Escribe cualquier tema o pregunta sobre los 4 programas electorales descargados (por ejemplo: pensiones, vivienda, impuestos, sanidad, educación o inmigración).",
                "key_differences": [],
                "party_comparisons": [],
                "sources": [],
                "suggested_followups": [
                    "¿Qué diferencias hay en las pensiones?",
                    "Compara las propuestas de vivienda y alquiler",
                    "¿Qué propone cada partido sobre impuestos (IRPF e IVA)?",
                ],
            }

        if self.is_greeting(q):
            return {
                "mode": "greeting",
                "impartial_notice": "Asistente estrictamente imparcial · Solo información verificada de los 4 programas 29N 2026.",
                "intro": "Hola. Soy el comparador imparcial de InfoElect. Puedo contrastar las propuestas de Frente Amplio, PP, PSOE y VOX basándome únicamente en los 4 programas electorales descargados, sin emitir opiniones ni recomendaciones de voto.",
                "key_differences": [],
                "party_comparisons": [],
                "sources": [],
                "suggested_followups": [
                    "¿Qué diferencias hay en las pensiones?",
                    "¿Qué propone cada partido sobre inmigración y fronteras?",
                    "Compara sanidad entre PP y PSOE",
                    "¿Qué dicen sobre la energía nuclear?",
                ],
            }

        parties = self.detect_parties(q, ui_parties)
        opinion_asked = self.is_opinion_prompt(q)
        primary_stems, expanded_stems = expand_query_tokens(q)

        # Pure opinion request with no policy substance -> polite impartial boundary
        opinion_stems = {
            "mejor", "peor", "buen", "mal", "vot", "voto", "votar", "eleg", "elegir",
            "elig", "recomend", "recomienda", "convien", "razon", "mient", "gan", "gana",
            "not", "nota", "rank", "ranking", "puntu", "opina", "opin", "piens", "prefier",
            "mojat", "posicionat", "favorit", "cree",
        }
        meaningful_policy_stems = [
            s for s in primary_stems
            if s not in opinion_stems and not any(s.startswith(os_) for os_ in ("mejor", "peor", "vot", "recomend", "opin", "piens", "prefier", "puntu"))
        ]
        if opinion_asked and len(meaningful_policy_stems) == 0:
            return {
                "mode": "impartial_boundary",
                "impartial_notice": "InfoElect es un comparador estrictamente imparcial: no valora, puntúa ni recomienda el voto a ningún partido.",
                "intro": "No puedo indicar qué partido o programa es mejor ni recomendar el sentido del voto. Mi función es exponer de forma neutral y verificable qué propone cada uno de los 4 programas electorales descargados para que puedas sacar tus propias conclusiones.",
                "key_differences": [
                    "Puedes preguntar por las diferencias en cualquier ámbito concreto (pensiones, vivienda, impuestos, sanidad, educación, inmigración, energía, empleo…).",
                    "También puedes pedir comparaciones específicas entre dos o más partidos (por ejemplo: «Compara PP y PSOE en vivienda»).",
                ],
                "party_comparisons": [],
                "sources": [],
                "suggested_followups": [
                    "¿Qué diferencias hay en las pensiones?",
                    "Compara las medidas de vivienda y alquiler",
                    "¿Qué propone cada partido sobre impuestos?",
                    "Diferencias en sanidad pública y listas de espera",
                ],
            }

        impartial_notice = None
        if opinion_asked:
            impartial_notice = (
                "Nota de imparcialidad: InfoElect no evalúa qué propuesta es «mejor» ni emite juicios de valor. "
                "A continuación se muestran únicamente las diferencias factuales según los programas oficiales."
            )

        # Check curated topic match + always fetch live BM25 excerpts for full auditability
        matched_topic, topic_score = self.match_curated_topic(q)

        # Detect if the query asks a narrow sub-question not covered directly by curated topic title
        # e.g. "energía nuclear", "okupación", "inteligencia artificial", "ceuta y melilla", "salud mental"
        live_results: dict[str, list[dict[str, Any]]] = {}
        for pid in parties:
            live_results[pid] = self.search_party_bm25(
                pid, primary_stems, expanded_stems, q, top_k=3
            )

        # Decide whether curated topic applies cleanly or pure live RAG is sharper
        use_curated = False
        if matched_topic is not None:
            # Check if query contains specific focus words that are OUTSIDE the curated topic's trigger set
            topic_vocab = set(
                tokenize(
                    " ".join(
                        matched_topic.get("exact_triggers", [])
                        + matched_topic.get("keywords", [])
                        + [matched_topic.get("title", "")]
                    ),
                    remove_stop=True,
                )
            )
            extra_specific = [
                s for s in meaningful_policy_stems
                if s not in topic_vocab and len(s) >= 4
            ]
            # Use curated topic if query aligns cleanly with it (0-1 minor extra words)
            if len(extra_specific) <= 1 or topic_score >= 4.0:
                use_curated = True

        party_comparisons = []
        all_sources = []

        if use_curated and matched_topic is not None:
            party_names_str = ", ".join(PARTY_META[p]["name"] for p in parties)
            intro = (
                f"Comparativa factual sobre **{matched_topic['title']}** según los programas electorales "
                f"oficiales del 29N 2026 de {party_names_str} (sin valoraciones ni opiniones):"
            )
            key_differences = matched_topic.get("key_differences", [])

            for pid in parties:
                pdata = matched_topic["parties"].get(pid)
                if pdata:
                    party_comparisons.append(
                        {
                            "party": pid,
                            "party_name": PARTY_META[pid]["name"],
                            "program_title": PARTY_META[pid]["program_title"],
                            "color": PARTY_META[pid]["color"],
                            "summary": pdata["summary"],
                            "points": pdata["points"],
                            "citations": pdata.get("citations", []),
                            "has_coverage": pdata.get("has_coverage", True),
                        }
                    )
                for chunk in live_results.get(pid, [])[:2]:
                    all_sources.append(chunk)

            followups = matched_topic.get("followups", [])
            return {
                "mode": "curated_rag",
                "topic": matched_topic["title"],
                "impartial_notice": impartial_notice,
                "intro": intro,
                "key_differences": key_differences,
                "party_comparisons": party_comparisons,
                "sources": all_sources,
                "suggested_followups": followups,
            }

        # Live Full-Corpus RAG comparison across all 395 pages of the 4 PDFs!
        total_hits = sum(len(v) for v in live_results.values())
        if total_hits == 0:
            return {
                "mode": "no_match",
                "impartial_notice": impartial_notice,
                "intro": (
                    f"No se han encontrado coincidencias directas para «{q}» en los 4 programas electorales descargados. "
                    "Prueba con términos más amplios o consulta uno de los ámbitos principales."
                ),
                "key_differences": [],
                "party_comparisons": [],
                "sources": [],
                "suggested_followups": [
                    "¿Qué diferencias hay en las pensiones?",
                    "Compara las propuestas de vivienda",
                    "¿Qué dicen sobre inmigración y fronteras?",
                    "Diferencias en educación y universidades",
                ],
            }

        parties_with_hits = [PARTY_META[p]["name"] for p in parties if live_results.get(p)]
        parties_without_hits = [PARTY_META[p]["name"] for p in parties if not live_results.get(p)]

        key_differences = []
        if parties_with_hits:
            key_differences.append(
                f"Se han localizado referencias directas en los programas de: {', '.join(parties_with_hits)}."
            )
        if parties_without_hits:
            key_differences.append(
                f"En la búsqueda textual sobre los documentos descargados no aparecen referencias directas con estos términos en: {', '.join(parties_without_hits)}."
            )
        key_differences.append(
            "Los extractos mostrados proceden literalmente de los PDFs oficiales descargados con indicación de página para verificación directa."
        )

        for pid in parties:
            hits = live_results.get(pid, [])
            if hits:
                pts = []
                cits = []
                for h in hits[:3]:
                    pts.append(
                        f"{self.summarize_snippet(h['text'], 300, focus_terms=primary_stems)} (pág. {h['doc_page']})"
                    )
                    cits.append(
                        {
                            "pdf_page": h["pdf_page"],
                            "doc_page": h["doc_page"],
                            "section": h["section"],
                        }
                    )
                    all_sources.append(h)
                party_comparisons.append(
                    {
                        "party": pid,
                        "party_name": PARTY_META[pid]["name"],
                        "program_title": PARTY_META[pid]["program_title"],
                        "color": PARTY_META[pid]["color"],
                        "summary": f"Según el programa electoral de {PARTY_META[pid]['name']} ({PARTY_META[pid]['program_title']}), se recogen las siguientes referencias sobre esta consulta:",
                        "points": pts,
                        "citations": cits,
                        "has_coverage": True,
                    }
                )
            else:
                party_comparisons.append(
                    {
                        "party": pid,
                        "party_name": PARTY_META[pid]["name"],
                        "program_title": PARTY_META[pid]["program_title"],
                        "color": PARTY_META[pid]["color"],
                        "summary": f"No se han localizado referencias explícitas a estos términos concretos en el programa electoral descargado de {PARTY_META[pid]['name']}.",
                        "points": [],
                        "citations": [],
                        "has_coverage": False,
                    }
                )

        party_names_str = ", ".join(PARTY_META[p]["name"] for p in parties)
        return {
            "mode": "live_bm25_rag",
            "topic": q,
            "impartial_notice": impartial_notice,
            "intro": f"Resultado de búsqueda comparativa imparcial sobre **«{q}»** en los programas electorales de {party_names_str}:",
            "key_differences": key_differences,
            "party_comparisons": party_comparisons,
            "sources": all_sources,
            "suggested_followups": [
                "¿Qué diferencias hay en las pensiones?",
                "¿Qué proponen sobre impuestos (IRPF e IVA)?",
                "Compara las medidas de sanidad",
            ],
        }

    def search_raw(self, query: str, party: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
        primary, expanded = expand_query_tokens(query)
        target_parties = [party] if party in PARTY_ORDER else PARTY_ORDER
        results = []
        per_party = limit if party else max(3, limit // len(target_parties))
        for pid in target_parties:
            results.extend(self.search_party_bm25(pid, primary, expanded, query, top_k=per_party))
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    def get_page(self, party_id: str, pdf_page: int) -> dict[str, Any] | None:
        pages = self.pages_text.get(party_id, [])
        if 1 <= pdf_page <= len(pages):
            return pages[pdf_page - 1]
        return None
