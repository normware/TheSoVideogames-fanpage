# So Videogames Podcast - Workflow

```bash
python3 fetch.py                  # fetch/update episode data from RSS
python3 build.py                  # bake into index.html
python3 extract_games_flat.py     # extract games using GitHub Models API (free)
open index.html
```

`fetch.py` pulls RSS (paginated from page 0), sanitizes safe HTML tags, writes `episodes.json`. `build.py` reads that and writes `index.html` with search, highlights, dark mode, and episode-number filter. Count shows `N / 486 episodes`.

`extract_games_flat.py` reads `episodes.json` and outputs `games_flat.json` — a flat dict mapping episode numbers to arrays of game titles extracted via the GitHub Models API (free). Run with `--force` to re-process all episodes.

## Notes

- RSS returns 366 / 486 episodes (pre-2019 not in feed)
- HTML descriptions preserved in `index.html`
- Game extraction uses GitHub Models API (free) via `GITHUB_TOKEN`
