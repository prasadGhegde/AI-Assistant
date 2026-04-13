#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from morning_briefs.config import load_config
from morning_briefs.narration import NarrationPlanner


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print sample controlled-randomized Morning Briefs narration openings."
    )
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    config = load_config()
    planner = NarrationPlanner(config)
    recent = []
    now = datetime.now(config.timezone)
    for index in range(max(args.count, 1)):
        plan = planner.select(
            now + timedelta(minutes=index),
            persist=False,
            recent_selections=recent,
        )
        recent.append(plan.to_dict())
        print(f"{index + 1}. {plan.opening_line} {plan.intro_line}")
        print(f"   Weather: {plan.weather_transition}")
        print(f"   Close: {plan.closing_line}")


if __name__ == "__main__":
    main()
