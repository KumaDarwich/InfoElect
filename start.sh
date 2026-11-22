#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/backend"
PORT="${PORT:-8000}"
echo "Iniciando InfoElect en http://localhost:${PORT} ..."
exec python3 -m uvicorn server:app --host 0.0.0.0 --port "${PORT}"
