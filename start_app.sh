#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
  PYTHON_CMD=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1 && python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo
  echo "Python 3.10 or newer was not found."
  echo "Run sh install_app.sh first."
  echo
  exit 1
fi

echo
echo " Pub Assist"
echo " ----------"
echo " Using: $PYTHON_CMD"
echo " If dependencies are missing, run sh install_app.sh first."
echo
echo " Starting server at http://127.0.0.1:7654"
echo " Press Ctrl+C to stop."
echo

"$PYTHON_CMD" -m uvicorn app:app --host 127.0.0.1 --port 7654
