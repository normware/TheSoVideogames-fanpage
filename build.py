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
    """Compute oldschool list facts from the episode/game data."""
    stats = []

    def link(n, text):
        return '<a href="#ep-{0}" data-ep="{0}">{1}</a>'.format(n, html.escape(text))

    def ep_row(n, extra=""):
        e = by_num.get(n)
        if not e:
            return '<div class="srow">#{0} {1}</div>'.format(n, extra)
        return ('<div class="srow">' + link(n, "Ep. " + str(n)) +
                ' <span class="sval">' + html.escape(_short_title(e)) + '</span> ' +
                html.escape(e.get("date") or "") + ' ' + extra + '</div>')

    def ep_on_date(d):
        for e in eps_num:
            if e.get("date") == d.isoformat():
                return _ep_int(e)
        return None

    def parse_ep_date(e):
        d = e.get("date")
        if not d:
            return None
        try:
            return date.fromisoformat(d)
        except ValueError:
            return None

    eps_num = [e for e in eps if _ep_int(e) is not None]
    nums = sorted({_ep_int(e) for e in eps_num})
    bonus = [e for e in eps if e not in eps_num]
    by_num = {_ep_int(e): e for e in eps_num}
    top = max(nums) if nums else 0

    stats.append({
        "value": str(len(eps)),
        "label": "Episodes in the feed",
        "note": "{} numbered + {} bonus".format(len(eps_num), len(bonus)),
        "more": ('<div class="srow">Every show in the archive, newest first.</div>'
                 '<div class="srow">Numbered: <span class="sval">{0}</span> · Bonus/un-numbered: <span class="sval">{1}</span></div>'
                 '<div class="srow">Range: <span class="sval">#{2}</span> to <span class="sval">#{3}</span></div>').format(
                     len(eps_num), len(bonus),
                     min(nums) if nums else "-", max(nums) if nums else "-"),
    })

    if nums:
        first = min(nums)
        stats.append({
            "value": "#" + str(first),
            "label": "First episode in the archive",
            "note": _short_title(by_num[first]),
            "more": ep_row(first, "the very first show"),
        })

    dates = [d for d in (parse_ep_date(e) for e in eps) if d]
    dates.sort()

    if dates:
        span_years = (dates[-1] - dates[0]).days / 365.25
        stats.append({
            "value": "{:.0f} yrs".format(span_years),
            "label": "Show history",
            "note": "{} → {}".format(dates[0].isoformat(), dates[-1].isoformat()),
            "more": (ep_row(ep_on_date(dates[0]), "earliest in the feed") if ep_on_date(dates[0]) else "") +
                    (ep_row(ep_on_date(dates[-1]), "newest in the feed") if ep_on_date(dates[-1]) else ""),
        })

        dated_num = sorted(((parse_ep_date(e), _ep_int(e)) for e in eps_num if parse_ep_date(e)), key=lambda t: t[0])
        missing_nums = {_ep_int(e) for e in eps_num if not parse_ep_date(e)}
        clean_gaps = []
        for i in range(len(dated_num) - 1):
            d0, n0 = dated_num[i]
            d1, n1 = dated_num[i + 1]
            lo, hi = sorted((n0, n1))
            if any(lo < n < hi for n in missing_nums):
                continue
            clean_gaps.append((d1 - d0, d0, d1))
        if clean_gaps:
            gap, d0, d1 = max(clean_gaps, key=lambda t: t[0])
            g = gap.days
            stats.append({
                "value": "{:,} days".format(g),
                "label": "Longest hiatus",
                "note": "{} → {}".format(d0.isoformat(), d1.isoformat()),
                "more": '<div class="srow">Roughly <span class="sval">{} months</span> with no show.</div>'.format(round(g / 30.44)) +
                        (ep_row(ep_on_date(d0), "before the break") if ep_on_date(d0) else "") +
                        (ep_row(ep_on_date(d1), "back after the break") if ep_on_date(d1) else ""),
            })

    years = Counter(e.get("date", "")[:4] for e in eps if e.get("date"))
    if years:
        y, c = years.most_common(1)[0]
        rows = "".join(
            '<div class="srow syear"><span>{0}</span><span class="sval">{1} eps</span></div>'.format(yy, cc)
            for yy, cc in years.most_common(6))
        stats.append({
            "value": "{} eps".format(c),
            "label": "Busiest year",
            "note": y,
            "more": '<div class="srow">Top 6 years by episode count:</div>' + rows,
        })

    titles = sorted(eps, key=lambda e: len(e.get("title") or ""))
    if titles:
        long = titles[-1]
        ln = len(long.get("title") or "")
        if ln:
            stats.append({
                "value": "{} chars".format(ln),
                "label": "Longest title",
                "note": "#{}".format(long.get("episode")),
                "more": ('<div class="srow">Full title ({0} chars):</div>'
                        '<div class="srow"><span class="sval">{1}</span></div>').format(ln, html.escape(long.get("title") or "")) +
                        (ep_row(_ep_int(long)) if _ep_int(long) else ""),
            })

    descs = [(e, len(e.get("desc") or "")) for e in eps]
    if descs:
        de, dl = max(descs, key=lambda t: t[1])
        if dl:
            stats.append({
                "value": "{} chars".format(dl),
                "label": "Longest show notes",
                "note": "#{}".format(de.get("episode")),
                "more": (ep_row(_ep_int(de), "the longest notes") if _ep_int(de) else "") +
                        '<div class="srow">' + html.escape(
                            re.sub(r"\s+", " ", _clean_text(de.get("desc"))).strip()[:150]) + '…</div>',
            })

    total_desc = sum(len(e.get("desc") or "") for e in eps)
    stats.append({
        "value": "{:,} chars".format(total_desc),
        "label": "Total show notes",
        "note": "all episodes combined",
        "more": '<div class="srow">Average <span class="sval">{:,}</span> chars per episode.</div>'.format(
            round(total_desc / max(1, len(eps)))),
    })

    def mention_eps(word, cap=10):
        out = []
        for e in eps_num:
            if re.search(r"\b" + word + r"\b", _clean_text(e.get("desc"))):
                out.append(ep_row(_ep_int(e)))
                if len(out) >= cap:
                    break
        return "".join(out)

    alltext = " ".join(_clean_text(e.get("desc")) for e in eps)
    stats.append({
        "value": "{:,}×".format(alltext.count("carlos")),
        "label": "Carlos mentions",
        "note": "he even has a toggle button on this site",
        "more": mention_eps("carlos") + '<div class="srow">…and more.</div>',
    })

    e3_eps = [e for e in eps_num if re.search(r"\be3\b", (e.get("title") or "").lower())]
    stats.append({
        "value": str(len(e3_eps)),
        "label": "E3 episodes",
        "note": "E3 in the title · rest in peace",
        "more": "".join(ep_row(_ep_int(e)) for e in e3_eps[:15]) +
                ('<div class="srow">…and {} more.</div>'.format(len(e3_eps) - 15) if len(e3_eps) > 15 else ""),
    })

    reunion = next((e for e in eps if "reunion" in (e.get("title") or "").lower()), None)
    if reunion:
        stats.append({
            "value": "2020",
            "label": "Reunion special",
            "note": _short_title(reunion),
            "more": (ep_row(_ep_int(reunion), "reunion special") if _ep_int(reunion) else
                     '<div class="srow">' + html.escape(reunion.get("title") or "") + '</div>'),
        })

    gcounts = {k: len(v) for k, v in episode_games.items()
               if k.isdigit() and isinstance(v, list)}
    total = sum(gcounts.values())
    stats.append({
        "value": "{:,}".format(total),
        "label": "Game mentions",
        "note": "across the whole show",
        "more": '<div class="srow">Games named in the show notes, extracted per episode.</div>'
                '<div class="srow"><span class="sval">{:,}</span> episodes listed at least one game.</div>'.format(
                    sum(1 for v in gcounts.values() if v)),
    })

    distinct = len(game_posters)
    if not distinct:
        distinct = len({g for k, v in episode_games.items() if k.isdigit() and isinstance(v, list) for g in v})

    mention = Counter()
    for k, v in episode_games.items():
        if k.isdigit() and isinstance(v, list):
            for g in set(v):
                mention[g] += 1

    top5 = "".join(
        '<div class="srow"><span class="sval">{0}</span> — {1} eps</div>'.format(html.escape(g), c)
        for g, c in mention.most_common(5))
    stats.append({
        "value": "{:,}".format(distinct),
        "label": "Distinct games",
        "note": "unique titles ever discussed",
        "more": '<div class="srow">Top 5 by episode count:</div>' + top5,
    })

    if gcounts:
        top_num = max(gcounts, key=lambda k: gcounts[k])
        glist = "".join('<li>' + html.escape(g) + '</li>' for g in episode_games[top_num])
        stats.append({
            "value": str(gcounts[top_num]),
            "label": "Most games in one episode",
            "note": "Episode {}".format(top_num),
            "more": ep_row(int(top_num), "the whole game list") + '<ul class="glist">' + glist + '</ul>',
        })

        gc = [c for c in gcounts.values() if c]
        if gc:
            stats.append({
                "value": "{:.1f}".format(sum(gc) / len(gc)),
                "label": "Games per episode",
                "note": "episodes that discussed games",
                "more": '<div class="srow"><span class="sval">{:,}</span> episodes discussed at least one game.</div>'.format(len(gc)) +
                        '<div class="srow">Average <span class="sval">{:.1f}</span> games each.</div>'.format(sum(gc) / len(gc)),
            })

    if mention:
        top_game, top_count = mention.most_common(1)[0]
        eps_with = [k for k, v in episode_games.items()
                    if k.isdigit() and isinstance(v, list) and top_game in set(v)]
        rows = "".join(ep_row(int(k)) for k in sorted(eps_with, key=int)[:15])
        stats.append({
            "value": top_game,
            "label": "Most-discussed game",
            "note": "{} episodes".format(top_count),
            "more": '<div class="srow">Talked about in <span class="sval">{}</span> episodes:</div>'.format(len(eps_with)) + rows,
        })

        repeats = sum(1 for c in mention.values() if c >= 2)
        top10 = "".join(
            '<div class="srow"><span class="sval">{0}</span> — {1} eps</div>'.format(html.escape(g), c)
            for g, c in mention.most_common(10) if c >= 2)
        stats.append({
            "value": "{:,}".format(repeats),
            "label": "Repeat offenders",
            "note": "games discussed in 2+ episodes",
            "more": '<div class="srow">Top 10:</div>' + top10,
        })

        one_hit = sum(1 for c in mention.values() if c == 1)
        sample = [g for g, c in mention.items() if c == 1][:12]
        stats.append({
            "value": "{:,}".format(one_hit),
            "label": "One-hit wonders",
            "note": "games that only ever got a single mention",
            "more": '<div class="srow">A few of them:</div><ul class="glist">' +
                    "".join("<li>" + html.escape(g) + "</li>" for g in sample) + "</ul>",
        })

    with_poster = sum(1 for v in game_posters.values() if isinstance(v, dict) and v.get("poster"))
    if game_posters:
        stats.append({
            "value": "{}%".format(round(100 * with_poster / len(game_posters))),
            "label": "Findable on Steam",
            "note": "{} of {} games · {} too obscure".format(
                with_poster, len(game_posters), len(game_posters) - with_poster),
            "more": '<div class="srow">Games with a Steam capsule image for the poster grid.</div>'
                    '<div class="srow">The rest are hidden gems only the hosts know.</div>',
        })

    return stats


def render_stats_html(stats):
    rows = []
    for i, s in enumerate(stats, 1):
        summary = (
            "<summary>"
            + '<span class="idx">{:02d}</span>'.format(i)
            + '<span class="prompt">&gt;</span>'
            + '<span class="lbl">' + html.escape(s["label"]) + "</span>"
            + '<span class="val">' + html.escape(s["value"]) + "</span>"
            + (('<span class="nt">' + html.escape(s["note"]) + "</span>") if s.get("note") else "")
            + "</summary>"
        )
        more = s.get("more") or '<div class="srow">—</div>'
        rows.append(
            '<li class="stat-item"><details>' + summary +
            '<div class="stat-more">' + more + "</div></details></li>"
        )
    hint = "{} facts about the show — click a row to expand.".format(len(stats))
    return ('<div class="stats-hint">{}</div>'.format(html.escape(hint)) +
            '<ol class="stat-list">' + "".join(rows) + "</ol>")



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
    if e.get("episode"):
        out = ['<div class="ep" data-episode="{n}" id="ep-{n}">'.format(n=e["episode"])]
    else:
        out = ['<div class="ep">']
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
#toggle-posters, #carlos-toggle, .cat-toggle {{ background: none; border: 1px solid var(--border); color: var(--fg); cursor: pointer; font-size: 0.8rem; padding: 0.3rem 0.7rem; border-radius: 6px; }}
#toggle-posters:hover, #carlos-toggle:hover, .cat-toggle:hover {{ background: var(--card-bg); }}
#carlos-toggle.active, .cat-toggle.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
#cat-filters {{ display: inline-flex; gap: 0.4rem; flex-wrap: wrap; }}

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
.stats-hint {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted); font-size: 0.8rem; margin-bottom: 1rem; letter-spacing: 0.03em; }}
.stats-hint::before {{ content: "== "; }}
.stats-hint::after {{ content: " =="; }}
.stat-list {{ list-style: none; padding: 0; margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.85rem; }}
.stat-item {{ border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg); margin-bottom: 0.4rem; overflow: hidden; }}
.stat-item details > summary {{ list-style: none; cursor: pointer; display: flex; align-items: baseline; gap: 0.6rem; padding: 0.55rem 0.8rem; user-select: none; }}
.stat-item summary::-webkit-details-marker {{ display: none; }}
.stat-item[open] summary {{ border-bottom: 1px dashed var(--border); }}
.stat-item:hover {{ background: var(--card-hover); }}
.stat-item[open]:hover {{ background: var(--card-bg); }}
.stat-item .idx {{ color: var(--accent); opacity: 0.85; min-width: 2ch; }}
.stat-item .prompt {{ color: var(--muted); }}
.stat-item .lbl {{ flex: 1; min-width: 0; color: var(--fg); overflow-wrap: anywhere; }}
.stat-item .val {{ font-weight: 700; color: var(--fg); text-align: right; }}
.stat-item .nt {{ color: var(--muted); font-size: 0.8em; text-align: right; overflow-wrap: anywhere; }}
.stat-more {{ padding: 0.65rem 0.8rem 0.8rem 3.4rem; color: var(--muted); line-height: 1.65; font-size: 0.85rem; }}
.stat-more a {{ color: var(--link); text-decoration: none; border-bottom: 1px dotted var(--link); }}
.stat-more a:hover {{ border-bottom-style: solid; }}
.stat-more .srow {{ padding: 0.12rem 0; overflow-wrap: anywhere; }}
.stat-more .srow .sval {{ color: var(--fg); font-weight: 600; }}
.stat-more .srow.syear {{ display: flex; justify-content: space-between; gap: 1rem; max-width: 440px; }}
.stat-more .glist {{ list-style: none; padding: 0; margin: 0; columns: 2; column-gap: 1.5rem; }}
.stat-more .glist li {{ padding: 0.1rem 0; padding-left: 1em; text-indent: -1em; }}
.stat-more .glist li::before {{ content: "▸"; color: var(--accent); padding-right: 0.4em; font-size: 0.7em; }}

.footer {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--muted); text-align: center; line-height: 1.8; }}
.footer a {{ color: var(--link); }}
.footer .github {{ display: inline-flex; align-items: center; gap: 0.3rem; }}

#minimap {{ position: fixed; right: 12px; top: 50%; transform: translateY(-50%); height: 68vh; max-height: 460px; width: 34px; display: flex; flex-direction: column; align-items: center; gap: 6px; z-index: 50; }}
#mm-wheel {{ display: flex; gap: 1px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; line-height: 14px; height: 14px; overflow: hidden; background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 0 3px; color: var(--fg); user-select: none; }}
#mm-wheel .mm-digit {{ overflow: hidden; height: 14px; width: 8px; text-align: center; }}
#mm-wheel .mm-digit .mm-spool {{ display: flex; flex-direction: column; transition: transform 0.18s linear; }}
#mm-wheel .mm-digit .mm-spool span {{ height: 14px; line-height: 14px; display: block; }}
#mm-track {{ position: relative; flex: 1; width: 12px; background: var(--border); border-radius: 999px; cursor: pointer; }}
#mm-track .mm-tick {{ position: absolute; left: 0; right: 0; height: 1px; background: var(--muted); opacity: 0.6; }}
#mm-track .mm-tick:hover {{ background: var(--fg); opacity: 1; }}
#mm-track .mm-tick.active {{ background: var(--accent); opacity: 1; height: 2px; }}
#mm-track .mm-tick .mm-label {{ position: absolute; right: 16px; top: 50%; transform: translateY(-50%); font-size: 9px; color: var(--muted); white-space: nowrap; pointer-events: none; }}
#mm-indicator {{ position: absolute; left: -2px; right: -2px; height: 14px; border-radius: 999px; background: var(--accent); opacity: 0.25; pointer-events: none; transition: top 0.08s linear; }}
#minimap.hidden {{ display: none; }}

@media (max-width: 700px) {{
  .ep {{ flex-direction: column; gap: 0.75rem; }}
  .ep-posters {{ grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); }}
  .ep-posters img {{ width: 100%; }}
  .game-list {{ columns: 1; }}
  .stat-more {{ padding-left: 2.2rem; }}
  .stat-more .glist {{ columns: 1; }}
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
  <span id="cat-filters"></span>
</div>
<div id="results">{results_html}</div>
<div id="minimap" aria-hidden="true">
  <div id="mm-wheel">
    <div class="mm-digit"><div class="mm-spool"></div></div>
    <div class="mm-digit"><div class="mm-spool"></div></div>
    <div class="mm-digit"><div class="mm-spool"></div></div>
  </div>
  <div id="mm-track"></div>
</div>
<div id="stats-view">
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
  mmSetHidden();
}}
document.getElementById('tab-episodes').onclick = function() {{ showTab('episodes'); }};
document.getElementById('tab-stats').onclick = function() {{ showTab('stats'); }};

document.getElementById('stats-view').addEventListener('click', function(e) {{
  const a = e.target.closest('a[data-ep]');
  if (!a) return;
  e.preventDefault();
  showTab('episodes');
  const el = document.getElementById('ep-' + a.getAttribute('data-ep'));
  if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}});

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

// ---- minimap / scroll wheel ----
const mm = document.getElementById('minimap');
const mmTrack = document.getElementById('mm-track');
const mmWheel = document.getElementById('mm-wheel');
const mmStep = 25;
const mmSpools = Array.from(mmWheel.querySelectorAll('.mm-spool'));
mmSpools.forEach(function(spool) {{
  let s = '';
  for (let d = 0; d <= 9; d++) s += '<span>' + d + '</span>';
  spool.innerHTML = s + '<span>&nbsp;</span>';
}});
const mmStepPx = mmSpools[0] ? mmSpools[0].children[0].offsetHeight : 14;

let mmCards = [];
let mmHidden = false;
let mmDirty = false;

function mmSetHidden() {{
  const stats = document.getElementById('stats-view').classList.contains('vis');
  mm.classList.toggle('hidden', mmHidden || stats);
}}

function setWheel(num) {{
  for (let i = 0; i < 3; i++) {{
    const spool = mmSpools[i];
    const offset = (3 - String(num || 0).length);
    const digit = (num && i >= offset) ? parseInt(String(num)[i - offset]) : null;
    spool.style.transform = 'translateY(-' + (digit === null ? 10 : digit) * mmStepPx + 'px)';
  }}
}}

function updateMinimap() {{
  if (mmHidden || !mmCards.length) return;
  const y = window.scrollY + window.innerHeight * 0.12;
  let cur = mmCards[0];
  for (let i = 0; i < mmCards.length; i++) {{
    if (mmCards[i].top <= y) cur = mmCards[i];
    else break;
  }}
  setWheel(cur.num);
  const maxY = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
  let ind = document.getElementById('mm-indicator');
  if (!ind) {{
    ind = document.createElement('div');
    ind.id = 'mm-indicator';
    mmTrack.appendChild(ind);
  }}
  const idx = mmCards.indexOf(cur);
  const next = mmCards[idx + 1];
  const top = next ? (cur.top + next.top) / 2 : cur.top;
  ind.style.top = Math.round(100 * top / maxY) + '%';
  const ticks = mmTrack.querySelectorAll('.mm-tick');
  for (let i = 0; i < ticks.length; i++) {{
    ticks[i].classList.toggle('active', parseInt(ticks[i].dataset.num) === cur.num);
  }}
}}

function rebuildMinimap() {{
  mmDirty = false;
  mmTrack.innerHTML = '';
  mmCards = [];
  for (let i = 0; i < eps.length; i++) {{
    const el = eps[i];
    const num = parseInt(el.dataset.episode);
    if (el.style.display === 'none' || !num) continue;
    mmCards.push({{ num: num, el: el, top: el.offsetTop }});
  }}
  mmHidden = mmCards.length < 2;
  mmSetHidden();
  if (mmHidden) return;
  const maxNum = mmCards[0].num;
  const maxY = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
  for (let n = maxNum; n >= mmStep; n -= mmStep) {{
    const c = mmCards.find(function(x) {{ return x.num === n; }});
    if (!c) continue;
    const tick = document.createElement('div');
    tick.className = 'mm-tick';
    tick.dataset.num = n;
    const label = document.createElement('span');
    label.className = 'mm-label';
    label.textContent = n;
    tick.appendChild(label);
    tick.style.top = Math.round(100 * c.top / maxY) + '%';
    mmTrack.appendChild(tick);
  }}
  updateMinimap();
}}

function mmRefresh() {{
  if (mmDirty) return;
  mmDirty = true;
  requestAnimationFrame(rebuildMinimap);
}}

let mmTicking = false;
function onScroll() {{
  if (mmTicking) return;
  mmTicking = true;
  requestAnimationFrame(function() {{
    if (mmDirty) rebuildMinimap();
    else updateMinimap();
    mmTicking = false;
  }});
}}
window.addEventListener('scroll', onScroll, {{ passive: true }});

mmTrack.addEventListener('click', function(e) {{
  const tick = e.target.closest('.mm-tick');
  const target = tick
    ? mmCards.find(function(x) {{ return x.num === parseInt(tick.dataset.num); }})
    : mmCards[Math.round(((e.clientY - mmTrack.getBoundingClientRect().top) / mmTrack.getBoundingClientRect().height) * (mmCards.length - 1))];
  if (target) target.el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
}});

let carlosOnly = false;

const CATEGORIES = [
  {{ id: 'goty',     label: '🏆 GOTY',      re: /\\bgoty\\b|game of the year|pre-goty|top \d+ of \d{{4}}|best of the year/i }},
  {{ id: 'events',   label: '🎪 Events',    re: /\\bpax\\b|gamescom|summer game ?fest|state of play|nintendo direct|live from|recorded live/i }},
  {{ id: 'e3',       label: '🎮 E3',        re: /\\be3\\b/i }},
  {{ id: 'mailbag',  label: '💌 Mailbag',   re: /mail\\s*bag|mailbag|listener\\s*(?:created|qs?|questions?|mail)|fan\\s*mail|community|q\\s*&?\\s*a|\\bqa\\b|question\\s*time/i }},
  {{ id: 'specials', label: '🎁 Specials',  re: /\\bbonus\\b|\\bspecial\\b|micro-?sode/i }},
  {{ id: 'chicken',  label: '🐔 Chicken',   re: /chicken/i }},
  {{ id: 'trek',     label: '🪐 Star Trek', re: /star trek/i }},
  {{ id: 'unnumbered', label: '#️⃣ Unnumbered', re: null }},
];
const activeCats = new Set();
const epCats = eps.map(function(el) {{
  const a = el.querySelector('.ep-title a');
  const t = (a ? a.textContent : '').toLowerCase();
  const ids = [];
  for (let i = 0; i < CATEGORIES.length; i++) {{
    if (CATEGORIES[i].id === 'unnumbered') {{
      if (!el.dataset.episode) ids.push(CATEGORIES[i].id);
    }} else if (CATEGORIES[i].re.test(t)) {{
      ids.push(CATEGORIES[i].id);
    }}
  }}
  return ids;
}});

function renderCatButtons() {{
  const box = document.getElementById('cat-filters');
  for (let i = 0; i < CATEGORIES.length; i++) {{
    const c = CATEGORIES[i];
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'cat-toggle';
    b.dataset.cat = c.id;
    b.textContent = c.label;
    b.title = c.label.replace(/[^A-Za-z ]/g, '').trim() + ' episodes';
    b.onclick = function() {{
      if (activeCats.has(c.id)) {{ activeCats.delete(c.id); b.classList.remove('active'); }}
      else {{ activeCats.add(c.id); b.classList.add('active'); }}
      filter();
    }};
    box.appendChild(b);
  }}
}}

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
      mmRefresh();
    }};
    el.parentNode.insertBefore(tog, el.nextSibling);
  }}
  mmRefresh();
}}

window.SVG_onGames = function() {{ renderGameLists(); mmRefresh(); }};
window.SVG_onPosters = function() {{ renderGameLists(); renderPosterGrids(); mmRefresh(); }};
window.SVG_onDescriptions = function() {{ fillDescriptions(); refreshSearchText(); mmRefresh(); }};

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
    if (show && activeCats.size) {{
      show = epCats[i].some(function(id) {{ return activeCats.has(id); }});
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
  mmRefresh();
}}

let filterTimer;
function debounceFilter() {{
  clearTimeout(filterTimer);
  filterTimer = setTimeout(filter, 150);
}}
document.getElementById('search').addEventListener('input', debounceFilter);
document.getElementById('ep-filter').addEventListener('input', debounceFilter);
renderCatButtons();
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
