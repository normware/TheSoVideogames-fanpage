#!/usr/bin/env python3
"""Fetch RSS feed and update episodes.json idempotently."""

import urllib.request
import xml.etree.ElementTree as ET
import html, re, json, ssl, time, os

RSS_FEEDS = [
    ("https://gamecritics.com/category/podcasts/so-videogames/feed/", 50),
    ("https://gamecritics.com/podcasts/feed/", 80),
]
NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
ctx = ssl._create_unverified_context()
EPISODES_FILE = "episodes.json"
EXPECTED_EPISODES = 486

months = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06",
          "Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}

SAFE_TAGS = {"p","br","b","i","em","strong","a","ul","ol","li","u","s",
             "blockquote","cite","code","pre","hr","sub","sup","span","div",
             "h1","h2","h3","h4","h5","h6","dl","dt","dd"}

def sanitize(raw):
    if not raw:
        return ""
    raw = html.unescape(raw)
    raw = re.sub(r'<(script|style|iframe|object|embed|form|input|textarea|select|option|noscript)[^>]*>.*?</\1>', '', raw, flags=re.IGNORECASE|re.DOTALL)
    raw = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'</?([a-zA-Z][a-zA-Z0-9]*)[^>]*>', lambda m: m.group(0) if m.group(1).lower() in SAFE_TAGS else '', raw)
    raw = re.sub(r'<p>\s*</p>', '', raw)
    return raw.strip()

def extract_episode(title):
    m = re.search(r'(?:Episode|Ep|So\s*Videogames?)\s*(\d+)(?:\s*[:\s–-]|$)', title, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(\d{3})\b', title)
    if m:
        return int(m.group(1))
    return None

def parse_item(item):
    url = item.findtext("link", "")
    content_el = item.find("content:encoded", NS)
    desc = sanitize(content_el.text if content_el is not None else item.findtext("description", ""))
    desc = re.sub(r'\s*<p>\s*The post\s+.*?appeared first on\s+.*?\.?\s*</p>\s*', '', desc, flags=re.IGNORECASE)
    desc = desc.strip()
    pub_date = item.findtext("pubDate", "")
    date = ""
    if pub_date:
        parts = pub_date.split()
        if len(parts) >= 4:
            date = f"{parts[3]}-{months.get(parts[2],'00')}-{parts[1].zfill(2)}"
    title = item.findtext("title", "")
    return {
        "title": title,
        "episode": extract_episode(title),
        "desc": desc,
        "date": date,
        "url": url,
    }

def sort_key(e):
    n = e.get("episode")
    if n is not None:
        return (0, -int(n))
    d = e.get("date", "").replace("-", "")
    return (1, -(int(d) if d.isdigit() else 0))


def dedupe_by_number(eps):
    """Same episode number can appear in both the GC Podcast and So… Videogames feeds.
    Keep one entry per number, preferring the GameCritics.com Podcast title."""
    best = {}
    for e in eps:
        n = e.get("episode")
        if n is None:
            best.setdefault(("u", e["url"]), e)
            continue
        key = ("n", n)
        cur = best.get(key)
        if cur is None:
            best[key] = e
        else:
            cur_is_gc = "gamecritics.com podcast" in cur["title"].lower()
            new_is_gc = "gamecritics.com podcast" in e["title"].lower()
            if not cur_is_gc and new_is_gc:
                best[key] = e
    return list(best.values())


def fetch_rss():
    eps = []
    seen = set()
    for rss_url, max_pages in RSS_FEEDS:
        label = rss_url.split("/")[-3]
        for page in range(max_pages):
            try:
                with urllib.request.urlopen(f"{rss_url}?paged={page}", context=ctx) as resp:
                    root = ET.fromstring(resp.read())
            except Exception:
                break
            items = root.findall(".//item")
            if not items:
                break
            for item in items:
                url = item.findtext("link", "")
                if url in seen:
                    continue
                title = item.findtext("title", "").lower()
                title_norm = re.sub(r"\s+", " ", title.replace("…", " "))
                is_svg = ("so videogames" in title_norm or "the so videogames" in title_norm
                          or re.search(r"\bsvg\b", title_norm))
                is_gcpod = (re.search(r"gamecritics(\.com)?\s*podcast\b", title_norm)
                            or "gamecritics.com podcast" in title_norm)
                if not (is_svg or is_gcpod):
                    continue
                # skip GC Radio re-syndications and other shows (duplicate of numbered SVG eps)
                if re.search(r"gamecritics(\.com)?\s*radio", title_norm):
                    continue
                if "bridge crew" in title_norm or "transcript" in title_norm:
                    continue
                # skip WordPress archive pagination placeholder items (e.g. "… Podcast – Page 2")
                if re.search(r"[–—-]\s*page\s*\d+\s*$", title_norm):
                    continue
                seen.add(url)
                eps.append(parse_item(item))
            print(f"  {label} page {page}: {len(items)} items ({len(eps)} unique)")
            time.sleep(0.2)
    eps.sort(key=sort_key)
    return dedupe_by_number(eps)


def merge(existing, fresh):
    by_url = {e["url"]: e for e in existing}
    for e in fresh:
        if e["url"] not in by_url:
            by_url[e["url"]] = e
    return sorted(dedupe_by_number(by_url.values()), key=sort_key)
def load_existing():
    if os.path.exists(EPISODES_FILE):
        with open(EPISODES_FILE) as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    print("Fetching RSS feed...")
    fresh = fetch_rss()
    print(f"  {len(fresh)} episodes in feed")
    existing = load_existing()
    merged = merge(existing, fresh)
    print(f"  {len(existing)} existing → {len(merged)} total")
    # Re-extract episode numbers for all entries (handles regex improvements)
    for e in merged:
        e["episode"] = extract_episode(e["title"])
    with open(EPISODES_FILE, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    if len(merged) > len(existing):
        print(f"  +{len(merged) - len(existing)} new episode(s)")
    print(f"Done. {len(merged)} / {EXPECTED_EPISODES} episodes")
