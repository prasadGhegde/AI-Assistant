#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/prasadhegde/Documents/MorningBriefs"
cd "$PROJECT_DIR"

mkdir -p logs

if [[ -f ".venv/bin/activate" ]]; then
  source ".venv/bin/activate"
  PYTHON_BIN="python"
else
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" -m morning_briefs run --play >> logs/daily.log 2>&1
