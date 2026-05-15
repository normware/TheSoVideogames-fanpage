#!/usr/bin/env python3
"""Merge manual game overrides into games_flat.json's known-game pool, then clear the override file.

Override games are injected under the "__manual__" key in games_flat.json so
backfill_games.py picks them up and scans all episode descriptions for them."""

import json
from pathlib import Path

OVERRIDES = "games_overrides.json"
GAMES_FLAT = "games_flat.json"
MANUAL_KEY = "__manual__"


def main():
    if not Path(OVERRIDES).exists() or not Path(GAMES_FLAT).exists():
        return

    with open(OVERRIDES) as f:
        overrides = json.load(f)

    # Empty dict (legacy format) or empty list → nothing to do
    if not overrides:
        return

    if not isinstance(overrides, list):
        print(f"Warning: {OVERRIDES} should be a list of game titles, got {type(overrides).__name__}")
        return

    with open(GAMES_FLAT) as f:
        flat = json.load(f)

    existing = flat.get(MANUAL_KEY, [])
    existing_lower = {g.lower() for g in existing}
    new = [g for g in overrides if isinstance(g, str) and g.lower() not in existing_lower]

    if new:
        flat[MANUAL_KEY] = existing + new
        with open(GAMES_FLAT, "w") as f:
            json.dump(flat, f, indent=2, ensure_ascii=False)
        print(f"Added {len(new)} override game(s) to the known-game pool for backfill")

    with open(OVERRIDES, "w") as f:
        json.dump([], f, indent=2)
    print(f"Cleared {OVERRIDES}")


if __name__ == "__main__":
    main()
