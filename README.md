# So Videogames Podcast – Fan Page

Searchable episode listing with game title extraction, Steam enrichment, and poster thumbnails for the [So Videogames Podcast](https://gamecritics.com/category/podcasts/so-videogames/).

**Live at:** [sovideogames-fanpage.normware.org](https://sovideogames-fanpage.normware.org)

## Workflow

```bash
python3 fetch.py                  # fetch/update episode data from RSS
python3 extract_games_flat.py     # extract game titles using GitHub Models API (free)
python3 merge_overrides.py        # apply manual game overrides
python3 backfill_games.py         # backfill games LLM missed into other episodes
python3 distinct_games.py         # build distinct game list
python3 enrich_games.py           # fetch poster URLs from Steam API (free)
python3 build.py                  # bake everything into index.html
open index.html
```

## Pipeline

| Step | Script | Input | Output |
|---|---|---|---|
| 1 | `fetch.py` | RSS feed | `episodes.json` |
| 2 | `extract_games_flat.py` | `episodes.json` | `games_flat.json` — per-episode game title arrays via LLM |
| 3 | `merge_overrides.py` | `games_overrides.json` | merged into `games_flat.json`, then cleared |
| 4 | `backfill_games.py` | `games_flat.json` + `episodes.json` | scans descriptions for known games the LLM missed |
| 5 | `distinct_games.py` | `games_flat.json` | `distinct_games.json` — alphabetically sorted unique games |
| 6 | `enrich_games.py` | `distinct_games.json` | `games_enriched.json` — poster URLs via Steam API |
| 7 | `build.py` | all above | `index.html` — full site with search, dark mode, posters |

## Features

- **Search** — live filter across episode titles and descriptions
- **Dark/light mode** — persisted to localStorage
- **Episode number filter** — jump to a specific episode
- **Game list** — per-episode bullet list of mentioned games
- **Steam links** — known games link directly to their Steam store page
- **Poster thumbnails** — Steam capsule images in a 2-column grid (togglable, hidden by default)
- **Manual overrides** — add games the LLM missed via `games_overrides.json`

## Adding Missed Games

If the LLM didn't detect a game, add it to `games_overrides.json`:

```json
{
  "487": ["Max Payne 3", "Max Payne"],
  "486": ["Drill Core"]
}
```

Then re-run `python3 merge_overrides.py && python3 distinct_games.py && python3 enrich_games.py && python3 build.py`. The override file is cleared after merge.

## Notes

- **366 / 486** episodes in feed (pre-2019 not in RSS)
- Game extraction uses **GitHub Models API** (free) via `GITHUB_TOKEN`
- Poster enrichment uses **Steam Store API** (free, no key needed)
- Set `RAWG_API_KEY` env var for better poster coverage (free at rawg.io/apidocs)
- Game artwork © respective publishers
