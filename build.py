#!/usr/bin/env python3
"""Build index.html — premium podcast episode browser with game poster grid."""

import json
import re
import html
from collections import Counter
from datetime import date

EPISODES_FILE = "episodes.json"
GAMES_FLAT_FILE = "games_flat.json"
ENRICHED_FILE = "games_enriched.json"
EXPECTED_COUNT = None  # computed at build time from loaded data


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _clean_text(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).lower()


def _short_title(e):
    t = re.sub(r"(?i)^.*?episode\s*\d+[:.\-–—]*\s*", "", e.get("title") or "")
    t = re.sub(r"(?i)^so videogames\s*:?\s*", "", t)
    t = t.strip(" :-–—.")
    if len(t) > 40:
        t = t[:37] + "…"
    return t


def _ep_int(e):
    v = e.get("episode")
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    return None


def compute_stats(eps, episode_games, game_posters):
    """Compute 20 fun statistics from the episode/game data."""
    stats = []

    eps_num = [e for e in eps if _ep_int(e) is not None]
    nums = sorted({_ep_int(e) for e in eps_num})
    bonus = [e for e in eps if e not in eps_num]

    stats.append({
        "emoji": "🎙", "value": f"{len(eps):,}",
        "label": "Episodes in the feed",
        "note": f"{len(eps_num):,} numbered + {len(bonus)} bonus",
    })

    if nums:
        top = max(nums)
        e = next(x for x in eps_num if _ep_int(x) == top)
        stats.append({
            "emoji": "🆕", "value": f"#{top}",
            "label": "Newest episode",
            "note": f"{_short_title(e)} · {(e.get('date') or 'no date')[:7]}",
        })

    dates = []
    for e in eps:
        d = e.get("date")
        if d:
            try:
                dates.append(date.fromisoformat(d))
            except ValueError:
                pass
    dates.sort()

    if dates:
        span_years = (dates[-1] - dates[0]).days / 365.25
        stats.append({
            "emoji": "📅", "value": f"{span_years:.0f} yrs",
            "label": "Show history",
            "note": f"{dates[0].isoformat()} → {dates[-1].isoformat()}",
        })

        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        if gaps:
            g = max(gaps)
            i = gaps.index(g)
            stats.append({
                "emoji": "⏳", "value": f"{g:,} days",
                "label": "Longest hiatus",
                "note": f"{dates[i].isoformat()} → {dates[i + 1].isoformat()}",
            })

    years = Counter(e.get("date", "")[:4] for e in eps if e.get("date"))
    if years:
        y, c = years.most_common(1)[0]
        stats.append({
            "emoji": "📈", "value": f"{c} eps",
            "label": "Busiest year",
            "note": y,
        })

    in_range = [n for n in nums if 1 <= n <= 500]
    stats.append({
        "emoji": "🗄", "value": f"{500 - len(in_range):,}",
        "label": "Episode numbers missing",
        "note": "pre-2019 shows not in the archive",
    })

    titles = sorted(eps, key=lambda e: len(e.get("title") or ""))
    if titles:
        short, long = titles[0], titles[-1]
        sn, ln = len(short.get("title") or ""), len(long.get("title") or "")
        if ln:
            stats.append({
                "emoji": "📏", "value": f"{ln} chars",
                "label": "Longest title",
                "note": f"#{long.get('episode')} · {_short_title(long)}",
            })
        if sn < ln:
            stats.append({
                "emoji": "✂️", "value": f"{sn} chars",
                "label": "Shortest title",
                "note": f"#{short.get('episode')}",
            })

    alltext = " ".join(_clean_text(e.get("desc")) for e in eps)
    stats.append({
        "emoji": "🎤", "value": f"{alltext.count('brad'):,}×",
        "label": "Host shout-outs",
        "note": "“Brad” in the show notes",
    })
    stats.append({
        "emoji": "🤘", "value": f"{alltext.count('carlos'):,}×",
        "label": "Carlos mentions",
        "note": "he even has a toggle button on this site",
    })

    e3 = sum(1 for e in eps if re.search(r"\be3\b", (e.get("title") or "").lower()))
    stats.append({
        "emoji": "🏟", "value": f"{e3}",
        "label": "E3 episodes",
        "note": "E3 in the title · rest in peace",
    })

    reunion = next((e for e in eps if "reunion" in (e.get("title") or "").lower()), None)
    if reunion:
        stats.append({
            "emoji": "🤝", "value": "2020",
            "label": "Reunion special",
            "note": _short_title(reunion),
        })

    gcounts = {k: len(v) for k, v in episode_games.items()
               if k.isdigit() and isinstance(v, list)}
    total = sum(gcounts.values())
    stats.append({
        "emoji": "🕹", "value": f"{total:,}",
        "label": "Game mentions",
        "note": "across the whole show",
    })

    distinct = len(game_posters)
    if not distinct:
        distinct = len({g for k, v in episode_games.items() if k.isdigit() and isinstance(v, list) for g in v})
    stats.append({
        "emoji": "🎮", "value": f"{distinct:,}",
        "label": "Distinct games",
        "note": "unique titles ever discussed",
    })

    mention = Counter()
    for k, v in episode_games.items():
        if k.isdigit() and isinstance(v, list):
            for g in set(v):
                mention[g] += 1

    if gcounts:
        top_num = max(gcounts, key=lambda k: gcounts[k])
        stats.append({
            "emoji": "🧺", "value": f"{gcounts[top_num]}",
            "label": "Most games in one episode",
            "note": f"Episode {top_num}",
        })

        gc = [c for c in gcounts.values() if c]
        if gc:
            stats.append({
                "emoji": "➗", "value": f"{sum(gc) / len(gc):.1f}",
                "label": "Games per episode",
                "note": "episodes that discussed games",
            })

    if mention:
        top_game, top_count = mention.most_common(1)[0]
        stats.append({
            "emoji": "🏆", "value": top_game,
            "label": "Most-discussed game",
            "note": f"{top_count} episodes",
        })

        repeats = sum(1 for c in mention.values() if c >= 2)
        stats.append({
            "emoji": "🔁", "value": f"{repeats:,}",
            "label": "Repeat offenders",
            "note": "games discussed in 2+ episodes",
        })

        one_hit = sum(1 for c in mention.values() if c == 1)
        stats.append({
            "emoji": "🎲", "value": f"{one_hit:,}",
            "label": "One-hit wonders",
            "note": "games that only ever got a single mention",
        })

    with_poster = sum(1 for v in game_posters.values() if isinstance(v, dict) and v.get("poster"))
    if game_posters:
        stats.append({
            "emoji": "🖼", "value": f"{round(100 * with_poster / len(game_posters))}%",
            "label": "Findable on Steam",
            "note": f"{with_poster:,} of {len(game_posters):,} games · {len(game_posters) - with_poster:,} too obscure",
        })

    return stats


def render_stats_html(stats):
    cards = []
    for s in stats:
        cards.append(
            '<div class="stat-card">'
            '<div class="stat-emoji">' + html.escape(s["emoji"]) + '</div>'
            '<div class="stat-value">' + html.escape(s["value"]) + '</div>'
            '<div class="stat-label">' + html.escape(s["label"]) + '</div>'
            + (('<div class="stat-note">' + html.escape(s["note"]) + '</div>') if s.get("note") else '')
            + '</div>'
        )
    return '<div class="stats-grid">' + ''.join(cards) + '</div>'


def _esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _desc_tid(e):
    return "d" + re.sub(r"[^a-zA-Z0-9]", "", e.get("url") or "")


def _ep_html(e):
    tid = _desc_tid(e)
    title = _esc(e.get("title"))
    ep_label = "Ep. {}".format(e["episode"]) if e.get("episode") else ""
    extra = "".join(
        ' · <a href="{u}" target="_blank" style="color:var(--muted)">{l}</a>'.format(u=_esc(s.get("url")), l=_esc(s.get("label")))
        for s in (e.get("sources") or [])[1:]
    )
    meta = (ep_label + " · " if ep_label else "") + _esc(e.get("date")) + extra
    out = ['<div class="ep" data-episode="{}">'.format(e["episode"]) if e.get("episode") else '<div class="ep">']
    out.append('<div class="ep-main">')
    out.append('<div class="ep-title"><a href="{u}" target="_blank">{t}</a></div>'.format(u=_esc(e.get("url")), t=title))
    out.append('<div class="ep-meta">{}</div>'.format(meta))
    out.append('<div class="desc" id="{}"></div>'.format(tid))
    out.append("</div>")
    out.append("</div>")
    return "".join(out)


def generate_html(eps, episode_games, game_posters, stats_html=""):
    highest = max((e.get("episode") or 0 for e in eps), default=0)
    results_html = "".join(_ep_html(e) for e in eps)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>So Videogames Podcast – Episodes</title>
<script src="games.js" defer></script>
<script src="posters.js" defer></script>
<script src="descriptions.js" defer></script>
<style>
:root {{
  color-scheme: dark;
  --bg: #0d0d0d;
  --fg: #e0e0e0;
  --border: #1f1f1f;
  --link: #70a0ff;
  --muted: #666;
  --accent: #70a0ff;
  --card-bg: #141414;
  --card-hover: #1a1a1a;
  --mark-bg: #554400;
}}
.light {{
  color-scheme: light;
  --bg: #f5f5f5;
  --fg: #1a1a1a;
  --border: #ddd;
  --link: #1a5cff;
  --muted: #888;
  --accent: #1a5cff;
  --card-bg: #fff;
  --card-hover: #fafafa;
  --mark-bg: #ffe066;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; background: var(--bg); color: var(--fg); line-height: 1.5; }}
h1 {{ font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; }}
.header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border); }}
#theme {{ background: none; border: 1px solid var(--border); color: var(--fg); cursor: pointer; font-size: 0.8rem; padding: 0.3rem 0.7rem; border-radius: 6px; }}
#theme:hover {{ background: var(--card-bg); }}
.search-row {{ display: flex; gap: 0.5rem; margin-bottom: 1rem; }}
#search {{ flex: 1; padding: 0.6rem 0.8rem; font-size: 0.95rem; background: var(--card-bg); color: var(--fg); border: 1px solid var(--border); border-radius: 6px; outline: none; }}
#search:focus {{ border-color: var(--accent); }}
#ep-filter {{ width: 100px; padding: 0.6rem; font-size: 0.95rem; background: var(--card-bg); color: var(--fg); border: 1px solid var(--border); border-radius: 6px; outline: none; text-align: center; }}
#ep-filter:focus {{ border-color: var(--accent); }}
.controls {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
#count {{ color: var(--muted); font-size: 0.85rem; }}
#toggle-posters, #carlos-toggle {{ background: none; border: 1px solid var(--border); color: var(--fg); cursor: pointer; font-size: 0.8rem; padding: 0.3rem 0.7rem; border-radius: 6px; }}
#toggle-posters:hover, #carlos-toggle:hover {{ background: var(--card-bg); }}
#carlos-toggle.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

.ep {{ display: flex; gap: 1.5rem; margin-bottom: 1.5rem; padding: 1.25rem; border-radius: 10px; background: var(--card-bg); border: 1px solid var(--border); transition: background 0.15s; }}
.ep:hover {{ background: var(--card-hover); }}
.ep-main {{ flex: 1; min-width: 0; }}
.ep-title {{ font-size: 1.05rem; font-weight: 600; margin-bottom: 0.2rem; }}
.ep-title a {{ color: var(--fg); text-decoration: none; }}
.ep-title a:hover {{ color: var(--link); }}
.ep-meta {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 0.6rem; }}
.game-list {{ list-style: none; padding: 0; margin: 0 0 0.4rem 0; columns: 2; column-gap: 1rem; }}
.game-list li {{ font-size: 0.85rem; padding: 0.1rem 0; padding-left: 1em; text-indent: -1em; color: var(--fg); }}
.game-list li::before {{ content: "▸"; color: var(--accent); padding-right: 0.4em; font-size: 0.7em; }}
.game-list li.known a {{ color: var(--fg); text-decoration: none; border-bottom: 1px dotted var(--muted); }}
.game-list li.known a:hover {{ color: var(--link); border-bottom-color: var(--link); }}
.game-list li .steam-badge {{ font-size: 0.65rem; color: var(--muted); margin-left: 0.3rem; }}
.desc {{ font-size: 0.85rem; line-height: 1.6; color: var(--muted); margin-top: 0.5rem; display: none; overflow-wrap: break-word; }}
.desc.vis {{ display: block; }}
.desc p {{ margin: 0.4em 0; }}
.desc a {{ color: var(--link); }}
.tog {{ color: var(--accent); cursor: pointer; font-size: 0.8rem; user-select: none; opacity: 0.7; }}
.tog:hover {{ opacity: 1; }}
mark {{ background: var(--mark-bg); color: inherit; }}

.ep-posters {{ display: none; grid-template-columns: 1fr 1fr; gap: 4px; align-content: start; flex-shrink: 0; }}
.ep-posters img {{ width: 110px; height: auto; border-radius: 4px; background: var(--border); display: block; }}
body.show-posters .ep-posters {{ display: grid; }}
.ep-posters img[src=""] {{ display: none; }}

.tabs {{ display: flex; gap: 0.5rem; margin-bottom: 1.25rem; }}
.tab {{ background: none; border: 1px solid var(--border); color: var(--muted); cursor: pointer; font-size: 0.85rem; padding: 0.4rem 0.9rem; border-radius: 999px; }}
.tab:hover {{ color: var(--fg); background: var(--card-bg); }}
.tab.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

#stats-view {{ display: none; }}
#stats-view.vis {{ display: block; }}
.stats-hint {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; }}
.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 0.75rem; }}
.stat-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; padding: 1rem; }}
.stat-card:hover {{ background: var(--card-hover); }}
.stat-emoji {{ font-size: 1.1rem; }}
.stat-value {{ font-size: 1.35rem; font-weight: 700; margin: 0.35rem 0 0.1rem; letter-spacing: -0.02em; overflow-wrap: anywhere; }}
.stat-label {{ font-size: 0.85rem; color: var(--muted); }}
.stat-note {{ font-size: 0.75rem; color: var(--muted); margin-top: 0.4rem; opacity: 0.8; }}

.footer {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--muted); text-align: center; line-height: 1.8; }}
.footer a {{ color: var(--link); }}
.footer .github {{ display: inline-flex; align-items: center; gap: 0.3rem; }}

@media (max-width: 700px) {{
  .ep {{ flex-direction: column; gap: 0.75rem; }}
  .ep-posters {{ grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); }}
  .ep-posters img {{ width: 100%; }}
  .game-list {{ columns: 1; }}
  .stats-grid {{ grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }}
  body {{ padding: 1rem; }}
}}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>So Videogames Podcast</h1>
    <div style="font-size:0.8rem;color:var(--muted);margin-top:0.1rem">
      Search for games discussed on the
      <a href="https://gamecritics.com/category/podcasts/so-videogames/" target="_blank" style="color:var(--link);text-decoration:none">So Videogames Podcast</a>
    </div>
  </div>
  <button id="theme">☀ Light</button>
</div>
<div class="tabs">
  <button class="tab active" id="tab-episodes">🎙 Episodes</button>
  <button class="tab" id="tab-stats">📊 Stats</button>
</div>
<div class="search-row">
  <input type="text" id="search" placeholder="Search episodes…" autofocus>
  <input type="number" id="ep-filter" placeholder="Ep #" min="1">
</div>
<div class="controls">
  <span id="count"></span>
  <button id="toggle-posters">Show posters</button>
  <button id="carlos-toggle">🤘 Carlos</button>
</div>
<div id="results">{results_html}</div>
<div id="stats-view">
  <div class="stats-hint">20 fun facts about the show, computed from the episode archive.</div>
  {stats_html}
</div>
<div class="footer">
  <span>made by a fan —</span>
  <a class="github" href="https://github.com/normware/TheSoVideogames-fanpage" target="_blank">
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8"/></svg>
    GitHub
  </a>
  <br>
  {len(eps)} episodes · highest: #{highest} · data from <a href="https://gamecritics.com/category/podcasts/so-videogames/">gamecritics.com</a>
  <br>
  <a href="https://normware.org/impressum">Impressum</a> · <a href="https://normware.org/datenschutz">Datenschutz</a>
  <br>
  Game artwork © respective publishers · Posters via <a href="https://store.steampowered.com">Steam</a>
</div>
<script>
let postersVisible = false;

(function initTheme() {{
  const t = document.getElementById('theme');
  if (localStorage.getItem('theme') === 'light') {{
    document.documentElement.classList.add('light');
    t.textContent = '☾ Dark';
  }}
  t.onclick = function() {{
    document.documentElement.classList.toggle('light');
    const isLight = document.documentElement.classList.contains('light');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    t.textContent = isLight ? '☾ Dark' : '☀ Light';
  }};
}})();

function showTab(name) {{
  const isStats = name === 'stats';
  document.getElementById('tab-episodes').classList.toggle('active', !isStats);
  document.getElementById('tab-stats').classList.toggle('active', isStats);
  document.getElementById('stats-view').classList.toggle('vis', isStats);
  const others = document.querySelectorAll('.search-row, .controls, #results');
  for (let i = 0; i < others.length; i++) {{
    others[i].style.display = isStats ? 'none' : '';
  }}
}}
document.getElementById('tab-episodes').onclick = function() {{ showTab('episodes'); }};
document.getElementById('tab-stats').onclick = function() {{ showTab('stats'); }};

const eps = Array.from(document.querySelectorAll('.ep'));

function refreshSearchText() {{
  searchText = eps.map(function(el) {{
    const titleEl = el.querySelector('.ep-title a');
    const descEl = el.querySelector('.desc');
    return ((titleEl ? titleEl.textContent : '') + ' ' + (descEl ? descEl.textContent : '')).toLowerCase();
  }});
}}
let searchText = [];
refreshSearchText();

let carlosOnly = false;

document.getElementById('toggle-posters').onclick = function() {{
  postersVisible = !postersVisible;
  this.textContent = postersVisible ? 'Hide posters' : 'Show posters';
  document.body.classList.toggle('show-posters', postersVisible);
}};

document.getElementById('carlos-toggle').onclick = function() {{
  carlosOnly = !carlosOnly;
  this.classList.toggle('active', carlosOnly);
  filter();
}};

function esc(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function hl(t, q) {{
  if (!q) return t;
  try {{ return t.replace(new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi'), '<mark>$1</mark>'); }}
  catch(e) {{ return t; }}
}}

function gameListHTML(games) {{
  const posters = window.SVG_POSTERS || {{}};
  let out = '<ul class="game-list">';
  for (let i = 0; i < games.length; i++) {{
    const g = games[i];
    const entry = posters[g];
    const hasSteam = entry && entry.steam_id;
    const name = esc(g);
    if (hasSteam) {{
      out += '<li class="known"><a href="https://store.steampowered.com/app/' + entry.steam_id + '" target="_blank" rel="noopener">' + name + '<span class="steam-badge">Steam</span></a></li>';
    }} else {{
      out += '<li>' + name + '</li>';
    }}
  }}
  return out + '</ul>';
}}

function renderGameLists() {{
  if (!window.SVG_GAMES) return;
  for (let i = 0; i < eps.length; i++) {{
    const el = eps[i];
    const num = el.dataset.episode;
    const games = window.SVG_GAMES[num];
    if (!games || !games.length) continue;
    const ul = document.createElement('div');
    ul.innerHTML = gameListHTML(games);
    const list = ul.firstElementChild;
    const existing = el.querySelector('.game-list');
    if (existing) {{
      existing.replaceWith(list);
    }} else {{
      const meta = el.querySelector('.ep-meta');
      meta.parentNode.insertBefore(list, meta.nextSibling);
    }}
  }}
  refreshSearchText();
}}

function renderPosterGrids() {{
  if (!window.SVG_GAMES || !window.SVG_POSTERS) return;
  for (let i = 0; i < eps.length; i++) {{
    const el = eps[i];
    const games = window.SVG_GAMES[el.dataset.episode];
    if (!games || !games.length) continue;
    const imgs = [];
    for (let j = 0; j < games.length; j++) {{
      const g = games[j];
      const entry = window.SVG_POSTERS[g];
      let url = entry ? entry.poster : null;
      if (!url && entry && entry.steam_id) {{
        url = 'https://shared.akamai.steamstatic.com/steam/apps/' + entry.steam_id + '/capsule_231x87.jpg';
      }}
      if (!url) continue;
      const steamLink = entry && entry.steam_id ? 'https://store.steampowered.com/app/' + entry.steam_id : null;
      const img = '<img src="' + esc(url) + '" alt="' + esc(g) + '" loading="lazy">';
      imgs.push(steamLink ? '<a href="' + steamLink + '" target="_blank" rel="noopener">' + img + '</a>' : img);
    }}
    if (!imgs.length) continue;
    const grid = document.createElement('div');
    grid.className = 'ep-posters';
    grid.innerHTML = imgs.join('');
    el.appendChild(grid);
  }}
}}

function fillDescriptions() {{
  const map = window.SVG_DESCRIPTIONS || {{}};
  for (const tid in map) {{
    const el = document.getElementById(tid);
    if (!el) continue;
    el.innerHTML = map[tid];
    const tog = document.createElement('div');
    tog.className = 'tog';
    tog.textContent = '▸ Show description';
    tog.onclick = function() {{
      el.classList.toggle('vis');
      tog.textContent = el.classList.contains('vis') ? '▾ Hide description' : '▸ Show description';
    }};
    el.parentNode.insertBefore(tog, el.nextSibling);
  }}
}}

window.SVG_onGames = function() {{ renderGameLists(); }};
window.SVG_onPosters = function() {{ renderGameLists(); renderPosterGrids(); }};
window.SVG_onDescriptions = function() {{ fillDescriptions(); refreshSearchText(); }};

function filter() {{
  const q = document.getElementById('search').value.toLowerCase().trim();
  const epNum = document.getElementById('ep-filter').value.trim();
  let count = 0;
  let anyShown = false;

  for (let i = 0; i < eps.length; i++) {{
    const el = eps[i];
    let show = true;
    if (q) {{
      show = searchText[i].includes(q);
    }}
    if (show && epNum) {{
      show = parseInt(el.dataset.episode) === parseInt(epNum);
    }}
    if (show && carlosOnly) {{
      show = searchText[i].includes('carlos');
    }}
    el.style.display = show ? '' : 'none';
    if (show) {{
      count++;
      anyShown = true;
      const link = el.querySelector('.ep-title a');
      if (link) {{
        link.innerHTML = q ? hl(esc(link.textContent), esc(q)) : esc(link.textContent);
      }}
    }}
  }}

  document.getElementById('count').textContent = count + ' / ' + eps.length + ' episodes';

  const r = document.getElementById('results');
  const nm = document.getElementById('no-match');
  if (!anyShown) {{
    if (!nm) {{
      const p = document.createElement('p');
      p.id = 'no-match';
      p.style.cssText = 'color:#666;padding:1rem 0';
      p.textContent = 'No matches';
      r.appendChild(p);
    }}
  }} else if (nm) {{
    nm.remove();
  }}
}}

let filterTimer;
function debounceFilter() {{
  clearTimeout(filterTimer);
  filterTimer = setTimeout(filter, 150);
}}
document.getElementById('search').addEventListener('input', debounceFilter);
document.getElementById('ep-filter').addEventListener('input', debounceFilter);
filter();
</script>
</body>
</html>"""


def main():
    print(f"Loading {EPISODES_FILE}...")
    eps = load_json(EPISODES_FILE)
    print(f"  {len(eps)} episodes loaded")

    episode_games = load_json(GAMES_FLAT_FILE)
    game_posters = load_json(ENRICHED_FILE)

    if episode_games:
        ep_with_data = sum(1 for k, v in episode_games.items() if k.isdigit() and v)
        print(f"  {ep_with_data} episodes with game data")
    if game_posters:
        with_poster = sum(1 for v in game_posters.values() if v.get("poster"))
        print(f"  {len(game_posters)} games enriched ({with_poster} with posters)")

    print("Computing statistics...")
    stats = compute_stats(eps, episode_games, game_posters)
    print(f"  {len(stats)} statistics")

    print("Generating index.html...")
    stats_html = render_stats_html(stats)
    html_out = generate_html(eps, episode_games, game_posters, stats_html)
    with open("index.html", "w") as f:
        f.write(html_out)
    print(f"Done. {len(eps)} episodes ({len(html_out)} bytes)")

    games = {k: v for k, v in episode_games.items() if k.isdigit() and v}
    descs = {_desc_tid(e): e["desc"] for e in eps if e.get("desc")}
    write_data_files(games, game_posters, descs)


def write_data_files(episode_games, game_posters, descs):
    files = {
        "games.js": "window.SVG_GAMES = {games};\nwindow.SVG_onGames && window.SVG_onGames();\n",
        "posters.js": "window.SVG_POSTERS = {posters};\nwindow.SVG_onPosters && window.SVG_onPosters();\n",
        "descriptions.js": "window.SVG_DESCRIPTIONS = {descs};\nwindow.SVG_onDescriptions && window.SVG_onDescriptions();\n",
    }
    payloads = {
        "games": json.dumps(episode_games),
        "posters": json.dumps(game_posters),
        "descs": json.dumps(descs),
    }
    for name, template in files.items():
        content = template.format(**payloads)
        with open(name, "w") as f:
            f.write(content)
        print(f"  {name}: {len(content)} bytes")


if __name__ == "__main__":
    main()
