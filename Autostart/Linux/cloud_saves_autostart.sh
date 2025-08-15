#!/usr/bin/env bash
set -euo pipefail

# Change if your venv is named differently; can also override:
# ENV_NAME=myenv ./cloud_saves_autostart.sh
ENV_NAME="${ENV_NAME:-linux_env}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project root is two levels up when script is Autostart/Linux/
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

# Activate venv if present, otherwise fall back to venv python path
if [[ -f "$PROJECT_DIR/$ENV_NAME/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "$PROJECT_DIR/$ENV_NAME/bin/activate"
  PYTHON_BIN="python3"
elif [[ -x "$PROJECT_DIR/$ENV_NAME/bin/python" ]]; then
  PYTHON_BIN="$PROJECT_DIR/$ENV_NAME/bin/python"
else
  echo "[ERROR] Virtual environment not found at $PROJECT_DIR/$ENV_NAME"
  exit 1
fi

# Run headless, survive logouts, no terminal pops
nohup "$PYTHON_BIN" "$PROJECT_DIR/auto.py" >/dev/null 2>&1 &
disown
