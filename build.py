#!/usr/bin/env python3
"""Build index.html — premium podcast episode browser with game poster grid."""

import json

EPISODES_FILE = "episodes.json"
GAMES_FLAT_FILE = "games_flat.json"
ENRICHED_FILE = "games_enriched.json"
EXPECTED_EPISODES = 486


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def generate_html(eps, episode_games, game_posters):
    data_json = json.dumps(eps)
    games_json = json.dumps(episode_games)
    posters_json = json.dumps(game_posters)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>So Videogames Podcast – Episodes</title>
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

.ep-posters {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px; align-content: start; flex-shrink: 0; }}
.ep-posters img {{ width: 110px; height: auto; border-radius: 4px; background: var(--border); display: block; }}
.ep-posters.hidden {{ display: none; }}
.ep-posters img[src=""] {{ display: none; }}

.footer {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--muted); text-align: center; line-height: 1.8; }}
.footer a {{ color: var(--link); }}
.footer .github {{ display: inline-flex; align-items: center; gap: 0.3rem; }}

@media (max-width: 700px) {{
  .ep {{ flex-direction: column; gap: 0.75rem; }}
  .ep-posters {{ grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); }}
  .ep-posters img {{ width: 100%; }}
  .game-list {{ columns: 1; }}
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
<div class="search-row">
  <input type="text" id="search" placeholder="Search episodes…" autofocus>
  <input type="number" id="ep-filter" placeholder="Ep #" min="1">
</div>
<div class="controls">
  <span id="count"></span>
  <button id="toggle-posters">Show posters</button>
  <button id="carlos-toggle">🤘 Carlos</button>
</div>
<div id="results"></div>
<div class="footer">
  <span>made by a fan —</span>
  <a class="github" href="https://github.com/normware/TheSoVideogames-fanpage" target="_blank">
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8"/></svg>
    GitHub
  </a>
  <br>
  {len(eps)} / {EXPECTED_EPISODES} episodes · data from <a href="https://gamecritics.com/category/podcasts/so-videogames/">gamecritics.com</a>
  <br>
  <a href="https://normware.org/impressum">Impressum</a> · <a href="https://normware.org/datenschutz">Datenschutz</a>
  <br>
  Game artwork © respective publishers · Posters via <a href="https://store.steampowered.com">Steam</a>
</div>
<script>
const episodes = {data_json};
const episodeGames = {games_json};
const gamePosters = {posters_json};

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

document.getElementById('toggle-posters').onclick = function() {{
  postersVisible = postersVisible ? false : true;
  this.textContent = postersVisible ? 'Hide posters' : 'Show posters';
  document.querySelectorAll('.ep-posters').forEach(p => p.classList.toggle('hidden', postersVisible ? false : true));
}};

let carlosOnly = false;
document.getElementById('carlos-toggle').onclick = function() {{
  carlosOnly = carlosOnly ? false : true;
  this.classList.toggle('active', carlosOnly);
  filter();
}};

function filter() {{
  const q = document.getElementById('search').value.toLowerCase().trim();
  const epNum = document.getElementById('ep-filter').value.trim();
  const r = document.getElementById('results');
  let f = episodes;
  if (q) {{
    f = f.filter(e => e.title.toLowerCase().includes(q) || (e.desc && e.desc.toLowerCase().includes(q)));
  }}
  if (epNum) {{
    f = f.filter(e => e.episode === parseInt(epNum));
  }}
  if (carlosOnly) {{
    f = f.filter(e => (e.title + ' ' + (e.desc || '')).toLowerCase().includes('carlos'));
  }}
  document.getElementById('count').textContent = f.length + ' / {EXPECTED_EPISODES} episodes';
  r.innerHTML = f.length ? f.map(e => epHTML(e, q)).join('') : '<p style="color:#666">No matches</p>';
}}

function esc(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function epHTML(e, q) {{
  const tid = 'd' + e.url.replace(/[^a-zA-Z0-9]/g, '');
  const title = hl(esc(e.title), esc(q));
  const epLabel = e.episode ? 'Ep. ' + e.episode : '';
  let desc = e.desc || '';
  const hlDesc = q ? hlDescText(desc, q) : desc;
  const vis = false;

  return '<div class="ep">'
    + '<div class="ep-main">'
    + '<div class="ep-title"><a href="' + e.url + '" target="_blank">' + title + '</a></div>'
    + '<div class="ep-meta">' + (epLabel ? epLabel + ' · ' : '') + e.date + '</div>'
    + gameList(e.episode, q)
    + (desc ? '<div id="' + tid + '" class="desc">' + hlDesc + '</div>' : '')
    + (desc ? '<div class="tog" onclick="var d=document.getElementById(\\'' + tid + '\\');d.classList.toggle(\\'vis\\');this.textContent=d.classList.contains(\\'vis\\')?\\'▾ Hide description\\':\\'▸ Show description\\'">▸ Show description</div>' : '')
    + '</div>'
    + posterGrid(e.episode)
    + '</div>';
}}

function gameList(epNum, q) {{
  const games = episodeGames[String(epNum)];
  if (!games || !games.length) return '';
  return '<ul class="game-list">' + games.map(g => {{
    const entry = gamePosters[g];
    const hasSteam = entry && entry.steam_id;
    const name = q ? hl(esc(g), esc(q)) : esc(g);
    if (hasSteam) {{
      return '<li class="known"><a href="https://store.steampowered.com/app/' + entry.steam_id + '" target="_blank" rel="noopener">' + name + '<span class="steam-badge">Steam</span></a></li>';
    }}
    return '<li>' + name + '</li>';
  }}).join('') + '</ul>';
}}

function posterGrid(epNum) {{
  const games = episodeGames[String(epNum)];
  if (!games || !games.length) return '';
  const imgs = games.map(g => {{
    const entry = gamePosters[g];
    let url = entry ? entry.poster : null;
    if (!url && entry && entry.steam_id) {{
      url = 'https://shared.akamai.steamstatic.com/steam/apps/' + entry.steam_id + '/capsule_231x87.jpg';
    }}
    if (!url) return '';
    const steamLink = entry && entry.steam_id ? 'https://store.steampowered.com/app/' + entry.steam_id : null;
    const img = '<img src="' + esc(url) + '" alt="' + esc(g) + '" loading="lazy">';
    return steamLink ? '<a href="' + steamLink + '" target="_blank" rel="noopener">' + img + '</a>' : img;
  }}).filter(s => s).join('');
  if (!imgs) return '';
  return '<div class="ep-posters' + (postersVisible ? '' : ' hidden') + '">' + imgs + '</div>';
}}

function hl(t, q) {{
  if (!q) return t;
  try {{ return t.replace(new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi'), '<mark>$1</mark>'); }}
  catch(e) {{ return t; }}
}}

function hlDescText(html, q) {{
  if (!q) return html;
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  walkText(tmp, q);
  return tmp.innerHTML;
}}

function walkText(node, q) {{
  if (node.nodeType === 3) {{
    const txt = node.textContent;
    if (txt.toLowerCase().includes(q)) {{
      const span = document.createElement('span');
      span.innerHTML = hl(esc(txt), esc(q));
      node.parentNode.replaceChild(span, node);
    }}
  }} else {{
    for (let i = node.childNodes.length - 1; i >= 0; i--) {{
      if (node.childNodes[i].nodeType !== 1 || !/^(script|style|iframe)$/i.test(node.childNodes[i].tagName)) {{
        walkText(node.childNodes[i], q);
      }}
    }}
  }}
}}

let filterTimer;
function debounceFilter() {{
  clearTimeout(filterTimer);
  filterTimer = setTimeout(filter, 200);
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
        print(f"  {len(episode_games)} episodes with game data")
    if game_posters:
        with_poster = sum(1 for v in game_posters.values() if v.get("poster"))
        print(f"  {len(game_posters)} games enriched ({with_poster} with posters)")

    print("Generating index.html...")
    html_out = generate_html(eps, episode_games, game_posters)
    with open("index.html", "w") as f:
        f.write(html_out)
    print(f"Done. {len(eps)} episodes ({len(html_out)} bytes)")


if __name__ == "__main__":
    main()
