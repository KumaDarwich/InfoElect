# InfoElect — Explorador Visual y Comparador Imparcial de Programas Electorales (29N 2026)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Offline Ready](https://img.shields.io/badge/Funciona-Sin%20API%20Keys-10B981)
![Imparcial](https://img.shields.io/badge/Enfoque-100%25%20Imparcial-0F172A)

**InfoElect** es una aplicación web de código abierto diseñada para explorar y comparar de forma **estrictamente imparcial, neutral y verificable** los 4 programas electorales oficiales de los principales partidos en las Elecciones Generales de España del **29 de noviembre de 2026**.

No requiere claves de API externas ni conexión a servicios de terceros: incluye el índice textual completo de las **395 páginas** oficiales en `data/` para que cualquier persona pueda clonarlo y usarlo en menos de un minuto.

---

## Funcionalidades principales

1. **Burbuja de selección de partido**
   - Pantalla inicial con 4 burbujas interactivas presentadas en **orden alfabético estricto** (*Frente Amplio, PP, PSOE, VOX*) con idéntico peso visual y sin valoraciones ni clasificaciones.
   - Selector flotante de burbujas en la cabecera y en el mapa para alternar entre partidos en cualquier momento.

2. **Mapa Visual interactivo por ámbitos**
   - Mapa mental radial interactivo (con zoom y arrastre) que conecta el partido seleccionado con **8 ámbitos principales**:
     - Economía y Fiscalidad
     - Vivienda
     - Sanidad
     - Educación
     - Inmigración y Fronteras
     - Empleo y Pensiones
     - Seguridad, Justicia y Estado
     - Energía, Familia y Medio Rural
   - **192 medidas verificadas** (6 medidas clave por ámbito y partido), todas con atribución explícita al programa correspondiente y botones de cita (`pág. X`) para leer el texto exacto de la página original.

3. **Comparativa 4×1 y Buscador literal en los programas**
   - Vista lado a lado de los 4 programas filtrable por ámbito.
   - Buscador de texto completo (BM25 en español) sobre **2.170 fragmentos semánticos** extraídos de las 395 páginas oficiales.

4. **Chatbot imparcial comparador (burbuja inferior derecha)**
   - Accesible desde cualquier vista mediante el botón flotante situado abajo a la derecha.
   - Responde preguntas comparativas (por ejemplo: *«¿Qué diferencias hay en las pensiones?»*, *«Compara PP y PSOE en vivienda»* o *«¿Qué dicen sobre la energía nuclear?»*) mostrando:
     - **Ejes objetivos de diferencia** entre los programas.
     - **Posición atribuida a cada partido** con citas de página verificables.
     - **Fragmentos literales** desplegables de los documentos oficiales.
   - **Protección contra sesgos:** si se le pregunta qué partido es «mejor» o a quién votar, rechaza emitir opiniones o recomendaciones y redirige a comparaciones factuales.

---

## Programas oficiales incluidos (orden alfabético)

Toda la información de InfoElect procede exclusivamente de los siguientes documentos oficiales del 29N 2026:

| Partido | Título del programa | Archivo PDF de referencia | Páginas |
| :--- | :--- | :--- | :---: |
| **Frente Amplio** | *Un programa como una casa* | `ProgramaFrenteAmplio.pdf` | 151 |
| **PP** | *Reconstrucción Nacional* | `PROGRAMA-ELECTORAL-PP-2026-RECONSTRUCCION-NACIONAL.pdf` | 64 |
| **PSOE** | *La fuerza de seguir avanzando* | `PROGRAMAPSOE29N26.pdf` | 114 |
| **VOX** | *Es Sentido Común* | `Programa-completo-A5-1.pdf` | 66 |

---

## Instalación y uso rápido

### Requisitos previos
- **Python 3.10 o superior** (`python3 --version`)
- Navegador web moderno (Chrome, Firefox, Edge, Safari)
- *(Opcional)* `poppler-utils` (`pdftotext`) únicamente si deseas reindexar tus propios PDFs desde cero.

### 1. Clonar el repositorio

```bash
git clone https://github.com/KumaDarwich/infoelect.git
cd infoelect
```

### 2. Instalar dependencias

#### En Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### En Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Iniciar la aplicación

#### En Linux / macOS
```bash
./start.sh
```
*(Puedes cambiar el puerto con `PORT=8080 ./start.sh`)*

#### En Windows (o manualmente en cualquier sistema)
```bash
cd backend
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

### 4. Abrir en el navegador

Accede a:

```text
http://localhost:8000
```

También puedes abrir enlaces directos a un partido, ámbito o consulta concreta mediante parámetros URL:
- `http://localhost:8000/?party=psoe&domain=sanidad`
- `http://localhost:8000/?view=compare&domain=economia`
- `http://localhost:8000/?party=pp&domain=empleo_pensiones&chat=¿Qué diferencias hay en las pensiones?`

---

## Uso opcional de los PDFs originales

El repositorio **ya incluye los datos preindexados** en `data/` (`programs_data.json`, `topics_knowledge.json`, `corpus_chunks.json` y `pages_text.json`), por lo que el mapa visual, la comparativa 4×1, el buscador literal, la vista de texto de cada página y el chatbot imparcial **funcionan nada más clonar el proyecto sin descargar los PDFs**.

Si además deseas habilitar el botón **«Abrir PDF original en esta página»** en el visor o regenerar el índice desde cero:

1. Descarga los 4 programas oficiales en PDF y colócalos en la carpeta `pdfs/` con estos nombres exactos:
   - `pdfs/frente_amplio.pdf`
   - `pdfs/pp.pdf`
   - `pdfs/psoe.pdf`
   - `pdfs/vox.pdf`
2. *(Opcional)* Para reconstruir el índice de búsqueda BM25 (requiere `pdftotext`):
   ```bash
   python3 backend/build_index.py
   ```

---

## Estructura del proyecto

```text
infoelect/
├── backend/
│   ├── server.py               # Servidor FastAPI (API REST + archivos estáticos)
│   ├── rag_engine.py           # Motor comparativo imparcial (BM25 + sinónimos + temas verificados)
│   ├── build_index.py          # Extractor e indexador de los PDFs oficiales
│   ├── build_programs_data.py  # Generador del dataset estructurado (192 medidas)
│   └── build_topics_data.py    # Generador de comparativas verificadas (17 bloques temáticos)
├── frontend/
│   ├── index.html              # Estructura principal de la interfaz
│   ├── styles.css              # Diseño editorial responsivo y burbujas interactivas
│   ├── app.js                  # Controlador de vistas, comparativa 4×1, buscador y visor de fuentes
│   ├── mindmap.js              # Renderizador SVG interactivo del mapa visual radial
│   └── chatbot.js              # Widget flotante inferior derecho del chatbot imparcial
├── data/
│   ├── programs_data.json      # 4 partidos × 8 ámbitos × 6 medidas verificadas
│   ├── topics_knowledge.json   # Comparativas imparciales verificadas por tema
│   ├── corpus_chunks.json      # 2.170 fragmentos semánticos indexados con página y sección
│   └── pages_text.json         # Texto limpio por página para consulta directa de citas
├── pdfs/                       # Carpeta opcional para colocar los 4 PDFs originales
├── requirements.txt            # Dependencias Python (FastAPI, Uvicorn, Pydantic)
├── start.sh                    # Script de arranque rápido para Linux/macOS
└── README.md
```

---

## Endpoints de la API

| Método | Ruta | Descripción |
| :---: | :--- | :--- |
| `GET` | `/api/health` | Estado del servidor y recuento de fragmentos/temas indexados |
| `GET` | `/api/programs` | Dataset completo de los 4 partidos y sus 8 ámbitos |
| `POST` | `/api/chat` | Comparador imparcial (`{"message": "...", "parties": null}`) |
| `GET` | `/api/search?q=...&party=...` | Búsqueda BM25 en las 395 páginas oficiales |
| `GET` | `/api/page/{party}/{pdf_page}` | Texto extraído de una página concreta del programa |
| `GET` | `/api/pdf/{party}` | Sirve el archivo PDF original (si está presente en `pdfs/`) |

---

## Compromiso de imparcialidad

- **Orden neutral:** los partidos aparecen siempre en orden alfabético (*Frente Amplio, PP, PSOE, VOX*).
- **Atribución explícita:** cada medida y respuesta atribuye el contenido directamente al programa electoral del partido correspondiente con número de página.
- **Sin opiniones ni rankings:** la aplicación no asigna notas, puntuaciones ni recomendaciones de voto.
- **Transparencia ante ausencias:** cuando un programa no incluye propuestas concretas sobre un tema consultado, el comparador lo indica expresamente en lugar de inferir posturas.

---

## Cómo contribuir o adaptarlo a otras elecciones

1. Haz un *fork* del repositorio y crea una rama (`git checkout -b mejora/nueva-funcionalidad`).
2. Para añadir nuevos programas o actualizar convocatorias futuras, sustituye los PDFs en `pdfs/`, actualiza `backend/build_index.py`, `backend/build_programs_data.py` y `backend/build_topics_data.py`, y regenera los JSON en `data/`.
3. Abre una *Pull Request* indicando las fuentes oficiales utilizadas.
