#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

echo
echo " Pub Assist"
echo " ----------"
echo " Install dependencies if needed:"
echo "   python -m pip install -r requirements_app.txt"
echo
echo " Starting server at http://127.0.0.1:7654"
echo " Press Ctrl+C to stop."
echo

python -m uvicorn app:app --reload --host 127.0.0.1 --port 7654
