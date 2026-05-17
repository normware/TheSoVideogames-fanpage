#!/usr/bin/env python3
"""Backfill games_flat.json: scan episode descriptions for known games the LLM missed."""

import json
import re
from pathlib import Path

EPISODES = "episodes.json"
GAMES_FLAT = "games_flat.json"


def clean(desc):
    if not desc:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', desc, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()


def main():
    if not Path(EPISODES).exists() or not Path(GAMES_FLAT).exists():
        return

    with open(EPISODES) as f:
        episodes = json.load(f)

    with open(GAMES_FLAT) as f:
        flat = json.load(f)

    # Build a lookup of episode number → clean description + title
    ep_desc = {}
    for ep in episodes:
        eid = str(ep.get("episode", ""))
        if eid:
            text = (ep.get("title", "") + " " + clean(ep.get("desc", ""))).lower()
            ep_desc[eid] = text

    # Build a set of all known game names (≥4 chars)
    known = set()
    for games in flat.values():
        for g in games:
            g = g.strip()
            if len(g) >= 4:
                known.add(g)

    # Skip known false positives (email, podcast name, generic terms)
    skip = {
        "sovideogamespodcast", "sovideogames", "so videogames",
        "podcast", "gmail", "com", "youtube", "twitter",
        "facebook", "instagram", "itunes", "spotify",
        "review", "gameplay", "walkthrough",
    }
    known = {g for g in known if g.lower().replace(" ", "") not in skip and g.lower() not in skip and not any(s == g.lower() for s in skip)}

    # Sort longest first so "Max Payne 3" matches before "Max Payne"
    known_sorted = sorted(known, key=len, reverse=True)

    total_added = 0
    for eid, desc in ep_desc.items():
        if not desc:
            continue
        existing = flat.get(eid, [])
        existing_lower = {g.lower() for g in existing}
        added = []
        for game in known_sorted:
            if game.lower() in existing_lower:
                continue
            pattern = r'\b' + re.escape(game) + r'\b'
            if re.search(pattern, desc, re.IGNORECASE):
                added.append(game)
                existing_lower.add(game.lower())
        if added:
            flat[eid] = existing + added
            total_added += len(added)

    if total_added:
        with open(GAMES_FLAT, "w") as f:
            json.dump(flat, f, indent=2, ensure_ascii=False)
        print(f"Backfilled {total_added} game mention(s) across {len([e for e in flat.values() if len(e) > 0])} episodes")
    else:
        print("No new games found by backfill")


if __name__ == "__main__":
    main()
