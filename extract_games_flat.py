#!/usr/bin/env python3
"""Extract games from episode descriptions using an LLM via the Groq API. Outputs flat JSON."""

import json
import argparse
import re
import os
import sys
import urllib.request, urllib.error
import time, ssl
from pathlib import Path

API_URL = "https://api.groq.com/openai/v1/chat/completions"
ctx = ssl._create_unverified_context()
EMPTY_KEY = "__empty__"


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
        if g.lower() in ('game', 'video game', 'games', 'gameplay', 'goty'):
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
            "Authorization": f"Bearer {token}",
            "User-Agent": "sovideogames-fanpage/1.0"
        }
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = json.loads(resp.read())
            raw = data["choices"][0]["message"]["content"]
            raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
            raw = re.sub(r'\s*```$', '', raw)
            result = json.loads(raw)
            games = result.get("games", []) if isinstance(result, dict) else []
            return post_process(games), True
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                wait = int(e.headers.get("Retry-After", "") or 0) if e.headers.get("Retry-After") else 0
                if not wait or wait <= 0:
                    wait = 30 * (attempt + 1)
                wait = min(wait, 120)
                print(f"\nRate limited on episode {episode.get('episode')}, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"\nError on episode {episode.get('episode')}: {e}")
                return [], False
        except Exception as e:
            print(f"\nError on episode {episode.get('episode')}: {e}")
            return [], False


def main():
    parser = argparse.ArgumentParser(description="Extract games → Flat JSON via Groq")
    parser.add_argument("-i", "--input", default="episodes.json", help="Input JSON file")
    parser.add_argument("-o", "--output", default="games_flat.json", help="Output flat JSON file")
    parser.add_argument("-m", "--model", default="llama-3.3-70b-versatile",
                        help="Groq model (default: llama-3.3-70b-versatile)")
    parser.add_argument("--token", default="",
                        help="Groq API key (defaults to GROQ_API_KEY env var)")
    parser.add_argument("--force", action="store_true",
                        help="Re-process ALL episodes (overwrite existing)")

    args = parser.parse_args()

    token = args.token or os.environ.get("GROQ_API_KEY") or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("Error: no Groq API key found. Set GROQ_API_KEY env var or pass --token.")
        return

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: {input_path} not found!")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        episodes = json.load(f)

    existing = {}
    empty_ids = set()
    if output_path.exists() and not args.force:
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            empty_ids = set(existing.get(EMPTY_KEY, []) or [])
        except:
            existing = {}

    to_process = []
    for ep in episodes:
        ep_id = str(ep["episode"])
        if args.force or ep_id not in existing or (not existing.get(ep_id) and ep_id not in empty_ids):
            to_process.append(ep)

    if not to_process:
        print("Nothing to process. Use --force to re-run everything.")
        return

    print(f"Processing {len(to_process)} episodes → {args.output} (model: {args.model})")

    results = existing.copy() if not args.force else {}
    failures = 0

    for i, ep in enumerate(to_process, 1):
        ep_id = str(ep["episode"])
        games, ok = extract_games(ep, args.model, token)
        if not ok:
            failures += 1
        else:
            if games:
                empty_ids.discard(ep_id)
            else:
                empty_ids.add(ep_id)
        results[ep_id] = games
        results[EMPTY_KEY] = sorted(empty_ids)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        if i % 10 == 0 or i == len(to_process):
            print(f"  {i}/{len(to_process)}")

        time.sleep(1.0)

    if to_process and failures == len(to_process):
        print(f"\nFATAL: all {failures} attempted episodes failed. API down or key invalid?")
        sys.exit(1)

    ep_keys = [k for k in results if not k.startswith("_")]
    total = sum(len(results[k]) for k in ep_keys)
    with_games = sum(1 for k in ep_keys if results[k])
    print(f"\nDone! {len(ep_keys)} episodes, {with_games} with games, {total} total game mentions")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
