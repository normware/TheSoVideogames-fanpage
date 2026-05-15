#!/usr/bin/env python3
"""Enrich distinct_games.json with poster URLs from Steam and RAWG APIs."""

import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

STEAM_SEARCH = "https://store.steampowered.com/api/storesearch/?term={}&cc=us&l=en"
RAWG_SEARCH = "https://api.rawg.io/api/games?key={}&search={}&page_size=1"

INPUT = "distinct_games.json"
OUTPUT = "games_enriched.json"

# macOS often has SSL cert issues; allow unverified for API calls
ctx = ssl._create_unverified_context()


def search_steam(game: str) -> dict:
    """Search Steam store. No key needed. Returns {steam_id, poster} or None."""
    try:
        url = STEAM_SEARCH.format(urllib.parse.quote(game))
        with urllib.request.urlopen(url, timeout=15, context=ctx) as r:
            data = json.loads(r.read())
        items = data.get("items", [])
        if items:
            item = items[0]
            poster = item.get("tiny_image", "")
            if poster:
                return {"steam_id": item.get("id"), "poster": poster}
    except Exception:
        pass
    return None


def search_rawg(game: str, key: str) -> dict:
    """Search RAWG. Needs free API key. Returns {rawg_id, poster} or None."""
    try:
        url = RAWG_SEARCH.format(key, urllib.parse.quote(game))
        with urllib.request.urlopen(url, timeout=10, context=ctx) as r:
            data = json.loads(r.read())
        results = data.get("results", [])
        if results:
            r = results[0]
            poster = r.get("background_image", "")
            return {"rawg_id": r["id"], "poster": poster}
    except Exception:
        pass
    return None


def main():
    rawg_key = os.environ.get("RAWG_API_KEY", "")

    if not Path(INPUT).exists():
        print(f"Error: {INPUT} not found. Run distinct_games.py first.")
        return

    with open(INPUT) as f:
        games = json.load(f)

    existing = {}
    if Path(OUTPUT).exists():
        with open(OUTPUT) as f:
            existing = json.load(f)

    enriched = {}
    count = 0

    for game in games:
        key = game.strip()
        if not key:
            continue

        # Skip if already cached
        if key in existing and existing[key].get("poster"):
            enriched[key] = existing[key]
            continue

        entry = {}

        # Try Steam first (free, no key needed)
        steam = search_steam(key)
        if steam:
            entry.update(steam)

        # Try RAWG if key available
        if rawg_key:
            rawg = search_rawg(key, rawg_key)
            if rawg and rawg.get("poster") and rawg["poster"].strip():
                entry.update(rawg)
                # Prefer RAWG poster (usually more game-specific)
                if rawg.get("poster"):
                    entry["poster"] = rawg["poster"]

        enriched[key] = entry if entry else {"poster": None}
        count += 1

        if count % 100 == 0:
            print(f"  {count}/{len(games)}")

        time.sleep(0.1)

    with open(OUTPUT, "w") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    with_poster = sum(1 for v in enriched.values() if v.get("poster"))
    print(f"\n{len(enriched)} games enriched ({with_poster} with posters) → {OUTPUT}")
    if not rawg_key:
        print("Tip: set RAWG_API_KEY for better coverage (free at rawg.io/apidocs)")


if __name__ == "__main__":
    main()
