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
    m = re.search(r'(?:Episode|So\s*Videogames?)?\s*(\d+)\s*[:\s–-]', title, re.IGNORECASE)
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
                if not any(kw in title for kw in ["so videogames", "gamecritics.com podcast", "the so videogames"]):
                    continue
                if "bridge crew" in title or "transcript" in title:
                    continue
                seen.add(url)
                eps.append(parse_item(item))
            print(f"  {label} page {page}: {len(items)} items ({len(eps)} unique)")
            time.sleep(0.2)
    eps.sort(key=lambda e: e.get("date", ""), reverse=True)
    return eps

def merge(existing, fresh):
    by_url = {e["url"]: e for e in existing}
    for e in fresh:
        if e["url"] not in by_url:
            by_url[e["url"]] = e
    return sorted(by_url.values(), key=lambda x: x.get("date", ""), reverse=True)

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
    with open(EPISODES_FILE, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    if len(merged) > len(existing):
        print(f"  +{len(merged) - len(existing)} new episode(s)")
    print(f"Done. {len(merged)} / {EXPECTED_EPISODES} episodes")
