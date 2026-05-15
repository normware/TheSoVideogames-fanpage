#!/usr/bin/env python3
"""Merge manual game overrides into games_flat.json, then clear the override file."""

import json
from pathlib import Path

OVERRIDES = "games_overrides.json"
GAMES_FLAT = "games_flat.json"


def main():
    if not Path(OVERRIDES).exists() or not Path(GAMES_FLAT).exists():
        return

    with open(OVERRIDES) as f:
        overrides = json.load(f)

    if not overrides:
        return

    with open(GAMES_FLAT) as f:
        flat = json.load(f)

    changed = 0
    for ep_id, games in overrides.items():
        if not isinstance(games, list):
            continue
        existing = flat.get(ep_id, [])
        existing_set = {g.lower() for g in existing}
        new = [g for g in games if g.lower() not in existing_set]
        if new:
            flat[ep_id] = existing + new
            changed += 1

    if changed:
        with open(GAMES_FLAT, "w") as f:
            json.dump(flat, f, indent=2, ensure_ascii=False)
        print(f"Merged overrides for {changed} episode(s)")

    # Clear overrides
    with open(OVERRIDES, "w") as f:
        json.dump({}, f, indent=2)
    print(f"Cleared {OVERRIDES}")


if __name__ == "__main__":
    main()
