#!/usr/bin/env bash
# Linux and macOS equivalent of run.bat.
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
PY="$VENV/bin/python"

if [ ! -x "$PY" ]; then
  echo "  Creating the virtual environment (one time only)..."
  python3 -m venv "$VENV"
fi

if ! "$PY" -c "import aiohttp, cryptography, qrcode, colorama" >/dev/null 2>&1; then
  echo "  Installing dependencies (one time only)..."
  "$PY" -m pip install --upgrade pip --quiet
  "$PY" -m pip install -r requirements.txt --quiet
fi

# No arguments: open the desktop app. Any argument means the caller wants the
# command line (ports, --no-stun, and so on).
if [ $# -eq 0 ]; then
  exec "$PY" -m librephonecam.gui
fi

exec "$PY" -m librephonecam "$@"
