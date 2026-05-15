# So Videogames Podcast - Workflow

```bash
python3 fetch.py                  # fetch/update episode data from RSS
python3 build.py                  # bake into index.html
python3 extract_games_flat.py     # extract games using GitHub Models API (free)
python3 merge_overrides.py        # apply manual game overrides
python3 backfill_games.py         # backfill games LLM missed into other episodes
python3 distinct_games.py         # build distinct game list
python3 enrich_games.py           # fetch poster URLs from Steam API
open index.html
```

`fetch.py` pulls RSS (paginated from page 0), sanitizes safe HTML tags, writes `episodes.json`. `build.py` reads that and writes `index.html` with search, highlights, dark mode, and episode-number filter. Count shows `N / 486 episodes`.

`extract_games_flat.py` reads `episodes.json` and outputs `games_flat.json` — a flat dict mapping episode numbers to arrays of game titles extracted via the GitHub Models API (free). Run with `--force` to re-process all episodes. `merge_overrides.py` reads `games_overrides.json` and merges any manual additions into `games_flat.json`, then clears the override file. `backfill_games.py` reads `games_flat.json` and scans episode descriptions for known game names the LLM might have missed, filling them in. `distinct_games.py` reads `games_flat.json` and outputs `distinct_games.json` — an alphabetically sorted list of all unique games. `enrich_games.py` reads `distinct_games.json` and fetches poster URLs from the Steam API (free, no key needed).

## Notes

- RSS returns 366 / 486 episodes (pre-2019 not in feed)
- HTML descriptions preserved in `index.html`
- Game extraction uses GitHub Models API (free) via `GITHUB_TOKEN`
