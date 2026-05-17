#!/usr/bin/env python3
"""Extract games from episode descriptions using LLM via GitHub Models API. Outputs flat JSON."""

import json
import argparse
import re
import os
import urllib.request
import time
from pathlib import Path

API_URL = "https://models.inference.ai.azure.com/chat/completions"


def clean_description(desc: str) -> str:
    if not desc:
        return ""
    text = re.sub(r'<br\s*/?>', '\n', desc, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()


def post_process(games: list) -> list:
    if not games:
        return []
    cleaned = []
    for g in games:
        g = g.strip(" .,!?;:\"'")
        g = re.sub(r'\s*\([^)]*\)\s*', ' ', g)
        g = re.sub(r'\s*\[[^\]]*\]\s*', ' ', g)
        g = re.sub(r'\s*[-–—]\s*(review|gameplay|DLC|update|impressions)\s*$', '', g, flags=re.I)
        g = re.sub(r'\s+', ' ', g).strip()
        if len(g) < 3:
            continue
        if g.lower() in ('game', 'video game', 'games', 'gameplay'):
            continue
        # Split merged entries joined by " & "
        if ' & ' in g and not any(x in g.lower() for x in ('& co', '& sons', '& ltd')):
            cleaned.extend([p.strip() for p in g.split('&')])
        else:
            cleaned.append(g)
    seen = set()
    out = []
    for g in cleaned:
        if g.lower() not in seen:
            seen.add(g.lower())
            out.append(g)
    return out


def extract_games(episode: dict, model: str, token: str) -> list:
    title = episode.get("title", "").strip()
    desc = clean_description(episode.get("desc", ""))
    text = (title + "\n" + desc).strip()
    if not text:
        return []

    system_prompt = (
        "You are an expert game title extractor. Extract ALL video game titles mentioned.\n\n"
        "Rules:\n"
        "- Return ONLY valid JSON: {\"games\": [\"Title 1\", \"Title 2\"]}\n"
        "- Include main titles AND any DLC/expansions mentioned\n"
        "- Keep subtitles as part of the title (e.g. \"Final Fantasy VII: Rebirth\")\n"
        "- Keep numbered entries separate (e.g. \"Max Payne 1 & 3\" → [\"Max Payne 1\", \"Max Payne 3\"])\n"
        "- Each line in a list is a separate game — never merge them\n"
        "- Strip annotations like (review), [DLC], - review from the title\n"
        "- Return empty array if none found"
    )

    body = json.dumps({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract all video game titles from:\n{text}"}
        ],
        "model": model,
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        raw = data["choices"][0]["message"]["content"]
        result = json.loads(raw)
        games = result.get("games", []) if isinstance(result, dict) else []
        return post_process(games)
    except Exception as e:
        print(f"\nError on episode {episode.get('episode')}: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Extract games → Flat JSON via GitHub Models")
    parser.add_argument("-i", "--input", default="episodes.json", help="Input JSON file")
    parser.add_argument("-o", "--output", default="games_flat.json", help="Output flat JSON file")
    parser.add_argument("-m", "--model", default="gpt-4o-mini",
                        help="GitHub Models model (default: gpt-4o-mini)")
    parser.add_argument("--token", default="",
                        help="GitHub token (defaults to GITHUB_TOKEN env var)")
    parser.add_argument("--force", action="store_true",
                        help="Re-process ALL episodes (overwrite existing)")

    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("Error: no GitHub token found. Set GITHUB_TOKEN env var or pass --token.")
        return

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: {input_path} not found!")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        episodes = json.load(f)

    existing = {}
    if output_path.exists() and not args.force:
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            existing = {}

    to_process = []
    for ep in episodes:
        ep_id = str(ep["episode"])
        if args.force or ep_id not in existing or not existing.get(ep_id):
            to_process.append(ep)

    if not to_process:
        print("Nothing to process. Use --force to re-run everything.")
        return

    print(f"Processing {len(to_process)} episodes → {args.output} (model: {args.model})")

    results = existing.copy() if not args.force else {}

    for i, ep in enumerate(to_process, 1):
        ep_id = str(ep["episode"])
        games = extract_games(ep, args.model, token)
        results[ep_id] = games

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        if i % 10 == 0 or i == len(to_process):
            print(f"  {i}/{len(to_process)}")

        time.sleep(0.25)

    total = sum(len(v) for v in results.values())
    with_games = sum(1 for v in results.values() if v)
    print(f"\nDone! {len(results)} episodes, {with_games} with games, {total} total game mentions")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
