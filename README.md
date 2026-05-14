# So Videogames Podcast - Episode Listing

Search UI for the So Videogames podcast archive. Opens by double-clicking `index.html` — no server needed.

```bash
python3 fetch.py    # fetch/update episode data from RSS
python3 build.py    # bake into index.html
open index.html
```

## Files

| File | Purpose |
|---|---|
| `index.html` | Episode listing with search + HTML descriptions (open this) |
| `episodes.json` | Cached episode data (title, description, episode #, date, url) |
| `fetch.py` | Fetches RSS feed, updates `episodes.json` idempotently |
| `build.py` | Reads `episodes.json` and generates `index.html` |

## Notes

- **366 / 486** episodes in feed (pre-2019 episodes not available via RSS)
- HTML descriptions preserved in `index.html`
