#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/prasadhegde/Documents/MorningBriefs"
cd "$PROJECT_DIR"

if [[ -f ".venv/bin/activate" ]]; then
  source ".venv/bin/activate"
  python -m morning_briefs dashboard
else
  python3 -m morning_briefs dashboard
fi
