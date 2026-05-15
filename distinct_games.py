#!/usr/bin/env python3
"""Build distinct_games.json — alphabetically sorted, deduplicated game list from games_flat.json."""

import json
from pathlib import Path

INPUT = "games_flat.json"
OUTPUT = "distinct_games.json"

def main():
    if not Path(INPUT).exists():
        print(f"Error: {INPUT} not found. Run extract_games_flat.py first.")
        return

    with open(INPUT) as f:
        data = json.load(f)

    seen = {}
    for ep_id, games in data.items():
        for g in games:
            key = g.strip().lower()
            if key and key not in seen:
                seen[key] = g.strip()

    distinct = sorted(seen.values(), key=lambda s: s.lower())

    with open(OUTPUT, "w") as f:
        json.dump(distinct, f, indent=2, ensure_ascii=False)

    print(f"{len(distinct)} distinct games → {OUTPUT}")

if __name__ == "__main__":
    main()
