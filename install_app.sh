#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

echo
echo " Pub Assist installer"
echo " --------------------"
echo

PYTHON_CMD=""

find_python() {
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
        PYTHON_CMD="$candidate"
        return 0
      fi
    fi
  done
  return 1
}

run_privileged() {
  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    "$@"
  fi
}

install_python() {
  os_name="$(uname -s 2>/dev/null || echo unknown)"

  if [ "$os_name" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      echo "Installing Python with Homebrew..."
      brew install python
      return $?
    fi
    echo "Python 3.10+ was not found, and Homebrew is not installed."
    echo "Install Python from https://www.python.org/downloads/ and run this installer again."
    if command -v open >/dev/null 2>&1; then
      open "https://www.python.org/downloads/"
    fi
    return 1
  fi

  if command -v apt-get >/dev/null 2>&1; then
    echo "Installing Python with apt..."
    run_privileged apt-get update
    run_privileged apt-get install -y python3 python3-venv python3-pip
  elif command -v dnf >/dev/null 2>&1; then
    echo "Installing Python with dnf..."
    run_privileged dnf install -y python3 python3-pip
  elif command -v yum >/dev/null 2>&1; then
    echo "Installing Python with yum..."
    run_privileged yum install -y python3 python3-pip
  elif command -v pacman >/dev/null 2>&1; then
    echo "Installing Python with pacman..."
    run_privileged pacman -Sy --needed python python-pip
  elif command -v zypper >/dev/null 2>&1; then
    echo "Installing Python with zypper..."
    run_privileged zypper install -y python3 python3-pip
  elif command -v apk >/dev/null 2>&1; then
    echo "Installing Python with apk..."
    run_privileged apk add python3 py3-pip
  else
    echo "Python 3.10+ was not found, and no supported package manager was detected."
    echo "Install Python from https://www.python.org/downloads/ and run this installer again."
    return 1
  fi
}

if ! find_python; then
  echo "Python 3.10 or newer was not found."
  install_python
  if ! find_python; then
    echo "Python installation finished, but Python 3.10+ is still not available on PATH."
    echo "Open a new terminal and run sh install_app.sh again."
    exit 1
  fi
fi

echo "Using Python command: $PYTHON_CMD"

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating local virtual environment in .venv..."
  if ! "$PYTHON_CMD" -m venv .venv; then
    if command -v apt-get >/dev/null 2>&1; then
      echo "Installing python3-venv and retrying..."
      run_privileged apt-get update
      run_privileged apt-get install -y python3-venv
      "$PYTHON_CMD" -m venv .venv
    else
      echo "Could not create .venv. Install your platform's Python venv package and run this installer again."
      exit 1
    fi
  fi
else
  echo "Reusing existing .venv."
fi

echo "Upgrading pip..."
.venv/bin/python -m pip install --upgrade pip

echo "Installing Pub Assist requirements..."
.venv/bin/python -m pip install -r requirements_app.txt

echo
echo "Pub Assist is ready."
echo "Launch it with:"
echo "  sh start_app.sh"
echo
