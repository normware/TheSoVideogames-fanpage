#!/usr/bin/env python3
"""Build index.html from episodes.json with search, highlights, dark mode."""

import json

EPISODES_FILE = "episodes.json"
EXPECTED_EPISODES = 486

def load_episodes():
    with open(EPISODES_FILE) as f:
        return json.load(f)

def generate_html(eps):
    data_json = json.dumps(eps)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>So Videogames Podcast – Episodes</title>
<style>
:root {{
  color-scheme: dark;
  --bg: #111;
  --fg: #ccc;
  --border: #2a2a2a;
  --link: #7cb4f7;
  --muted: #777;
  --tog: #888;
  --mark-bg: #554400;
  --card-bg: #181818;
}}
.light {{
  color-scheme: light;
  --bg: #fff;
  --fg: #222;
  --border: #ddd;
  --link: #1a0dab;
  --muted: #888;
  --tog: #666;
  --mark-bg: #ffe066;
  --card-bg: #fafafa;
}}
* {{ box-sizing: border-box; }}
body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 1rem; background: var(--bg); color: var(--fg); }}
h1 {{ font-size: 1.5rem; }}
#search {{ width: 100%; padding: 0.75rem; font-size: 1.2rem; margin-bottom: 0.5rem; box-sizing: border-box; background: var(--card-bg); color: var(--fg); border: 1px solid var(--border); border-radius: 6px; }}
#ep-filter {{ width: 100%; padding: 0.5rem; font-size: 1rem; margin-bottom: 1rem; box-sizing: border-box; background: var(--card-bg); color: var(--fg); border: 1px solid var(--border); border-radius: 6px; }}
.ep {{ margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border); }}
.ep-title {{ font-size: 1.1rem; font-weight: bold; }}
.ep-title a {{ color: var(--link); text-decoration: none; }}
.ep-title a:hover {{ text-decoration: underline; }}
.ep-meta {{ color: var(--muted); font-size: 0.85rem; margin: 0.15rem 0 0.5rem 0; }}
.desc {{ margin-top: 0.4rem; font-size: 0.9rem; line-height: 1.6; display: none; overflow-wrap: break-word; }}
.desc.vis {{ display: block; }}
.desc p {{ margin: 0.5em 0; }}
.desc ul, .desc ol {{ margin: 0.3em 0; padding-left: 1.5rem; }}
.desc li {{ margin: 0.15em 0; }}
.desc a {{ color: var(--link); }}
.tog {{ color: var(--tog); cursor: pointer; font-size: 0.85rem; user-select: none; }}
.tog:hover {{ text-decoration: underline; color: var(--fg); }}
.meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 1rem; }}
mark {{ background: var(--mark-bg); color: inherit; }}
.footer {{ margin-top: 2rem; font-size: 0.8rem; color: var(--muted); text-align: center; }}
.footer a {{ color: var(--link); }}
.header {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }}
#theme {{ background: none; border: 1px solid var(--border); color: var(--fg); cursor: pointer; font-size: 0.9rem; padding: 0.3rem 0.6rem; border-radius: 5px; white-space: nowrap; }}
#theme:hover {{ background: var(--card-bg); }}
.search-row {{ display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }}
.search-row input {{ flex: 1; }}
#ep-filter {{ width: 120px; flex: 0 0 auto; }}
.nav {{ display: flex; align-items: center; gap: 1rem; font-size: 0.85rem; margin-bottom: 1rem; color: var(--muted); }}
.nav a {{ color: var(--link); text-decoration: none; }}
.nav a:hover {{ text-decoration: underline; }}
.nav .sep {{ color: var(--border); }}
.nav .github {{ display: inline-flex; align-items: center; gap: 0.3rem; }}
</style>
</head>
<body>
<div class="header">
  <h1>So Videogames Podcast</h1>
  <button id="theme">☀ Light</button>
</div>
<div class="nav">
  <span>made by a fan —</span>
  <a class="github" href="https://github.com/normware/TheSoVideogames-fanpage" target="_blank">
    <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8"/></svg>
    GitHub
  </a>
</div>
<div class="search-row">
  <input type="text" id="search" placeholder="Search titles and descriptions…" autofocus>
  <input type="number" id="ep-filter" placeholder="Ep #" min="1">
</div>
<p class="meta" id="count"></p>
<div id="results"></div>
<div class="footer">
  {len(eps)} / {EXPECTED_EPISODES} episodes · data from <a href="https://gamecritics.com/category/podcasts/so-videogames/">gamecritics.com</a>
  <br>
  <a href="https://normware.org/impressum">Impressum</a> · <a href="https://normware.org/datenschutz">Datenschutz</a>
  · <a href="https://github.com/normware/TheSoVideogames-fanpage" target="_blank">GitHub</a>
</div>
<script>
const episodes = {data_json};

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
  document.getElementById('count').textContent = f.length + ' / {EXPECTED_EPISODES} episodes';
  r.innerHTML = f.length ? f.map(e => epHTML(e, q)).join('') : '<p style="color:#888">No matches</p>';
}}

function esc(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function epHTML(e, q) {{
  const tid = 'd' + e.url.replace(/[^a-zA-Z0-9]/g, '');
  const title = hl(esc(e.title), esc(q));
  const epLabel = e.episode ? 'Ep. ' + e.episode : '';
  let desc = e.desc || '';
  const inDesc = q && desc.toLowerCase().includes(q);
  const vis = q && !e.title.toLowerCase().includes(q) && inDesc;
  const hlDesc = q ? hlDescText(desc, q) : desc;
  return '<div class="ep"><div class="ep-title"><a href="' + e.url + '" target="_blank">' + title + '</a></div>'
    + '<div class="ep-meta">' + (epLabel ? epLabel + ' · ' : '') + e.date + '</div>'
    + (desc ? '<div id="' + tid + '" class="desc' + (vis ? ' vis' : '') + '">' + hlDesc + '</div>' : '')
    + (desc ? '<div class="tog" onclick="var d=document.getElementById(\\'' + tid + '\\');d.classList.toggle(\\'vis\\');this.textContent=d.classList.contains(\\'vis\\')?\\'▾ Hide\\':\\'▸ Show\\'">' + (vis ? '▾ Hide' : '▸ Show') + '</div>' : '')
    + '</div>';
}}

function hl(t, q) {{
  if (!q) return t;
  try {{ return t.replace(new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi'), '<mark class="hi">$1</mark>'); }}
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

document.getElementById('search').addEventListener('input', filter);
document.getElementById('ep-filter').addEventListener('input', filter);
filter();
</script>
</body>
</html>"""

if __name__ == "__main__":
    print(f"Loading {EPISODES_FILE}...")
    eps = load_episodes()
    print(f"  {len(eps)} episodes loaded")
    print("Generating index.html...")
    html_out = generate_html(eps)
    with open("index.html", "w") as f:
        f.write(html_out)
    print(f"Done. {len(eps)} episodes ({len(html_out)} bytes)")
