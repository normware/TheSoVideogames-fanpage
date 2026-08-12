#!/usr/bin/env python3
"""Backfill missing episode dates from source page metadata."""

import argparse
import json
import re
import ssl
import time
import urllib.request
from datetime import date

EPISODES_FILE = "episodes.json"
ctx = ssl._create_unverified_context()


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; SoVideogamesDateBackfill/1.0)",
    })
    with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, "replace")


def save_episodes(episodes):
    with open(EPISODES_FILE, "w") as f:
        json.dump(episodes, f, indent=2, ensure_ascii=False)
        f.write("\n")


def extract_date(page):
    patterns = [
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\'](\d{4}-\d{2}-\d{2})',
        r'<meta[^>]+content=["\'](\d{4}-\d{2}-\d{2})[^"\']*["\'][^>]+property=["\']article:published_time["\']',
        r'<meta[^>]+property=["\']og:article:published_time["\'][^>]+content=["\'](\d{4}-\d{2}-\d{2})',
        r'<meta[^>]+name=["\']date["\'][^>]+content=["\'](\d{4}-\d{2}-\d{2})',
        r'<time[^>]+datetime=["\'](\d{4}-\d{2}-\d{2})',
        r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})',
        r'"created_at"\s*:\s*"(\d{4}-\d{2}-\d{2})',
        r'"published_at"\s*:\s*"(\d{4}-\d{2}-\d{2})',
    ]
    for pat in patterns:
        m = re.search(pat, page, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def source_urls(ep):
    sources = ep.get("sources") or []
    gc = [s.get("url") for s in sources if "gamecritics.com" in (s.get("url") or "")]
    sc = [s.get("url") for s in sources if "soundcloud.com" in (s.get("url") or "")]
    fallback = [ep.get("url")] if ep.get("url") else []
    seen = set()
    for url in gc + fallback + sc:
        if url and url not in seen:
            seen.add(url)
            yield url


def ep_int(ep):
    n = ep.get("episode")
    return n if isinstance(n, int) else None


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def plausible_numbered_date(ep, value, episodes):
    n = ep_int(ep)
    d = parse_date(value)
    if n is None or d is None:
        return True
    lower = []
    upper = []
    for other in episodes:
        on = ep_int(other)
        od = parse_date(other.get("date"))
        if on is None or od is None or on == n:
            continue
        if on < n:
            lower.append(od)
        elif on > n:
            upper.append(od)
    if lower and d < max(lower):
        return False
    if upper and d > min(upper):
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Maximum missing-date entries to try.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(EPISODES_FILE) as f:
        episodes = json.load(f)

    missing = [e for e in episodes if not e.get("date") and list(source_urls(e))]
    if args.limit:
        missing = missing[:args.limit]

    filled = 0
    failed = 0
    for ep in missing:
        date = ""
        used = ""
        for url in source_urls(ep):
            try:
                date = extract_date(fetch(url))
            except Exception as exc:
                print(f"  ! {ep.get('episode') or '-'} {url}: {exc}", flush=True)
                continue
            if date:
                used = url
                break
        if date:
            if not plausible_numbered_date(ep, date, episodes):
                failed += 1
                print(f"  - {ep.get('episode') or '-'} implausible date {date}: {ep.get('title')} ({used})", flush=True)
                time.sleep(0.1)
                continue
            filled += 1
            print(f"  + {ep.get('episode') or '-'} {date} {ep.get('title')} ({used})", flush=True)
            if not args.dry_run:
                ep["date"] = date
                save_episodes(episodes)
        else:
            failed += 1
            print(f"  - {ep.get('episode') or '-'} no date found: {ep.get('title')}", flush=True)
        time.sleep(0.1)

    print(f"Done. filled={filled} failed={failed} remaining={sum(1 for e in episodes if not e.get('date'))}")


if __name__ == "__main__":
    main()
