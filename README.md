# Sweep Sotheby's — List Sotheby's luxury real‑estate app

A phone‑style, swipeable luxury real‑estate prototype for **List Sotheby's (LUXURY ESTATES)**,
imported from the Claude Design project *"sweep sotheby's app"*.

The UI is a multilingual (JA / EN / ZH / TH) property browser with:

- **Buy** — a Tinder‑style swipe deck of listings (save / skip / undo).
- **Sell** — a property‑submission form.
- **Rent** — a two‑column rental grid.
- **Search**, **Messages** (incl. an AI concierge chat), **Favorites**, and **Profile** tabs.

## Files

| File | Purpose |
| --- | --- |
| `sweep sotheby's.dc.html` | **Main implementation.** Full design‑canvas app: markup template + a `<script data-dc-script>` logic class (state, i18n data, all handlers). Uses the full‑resolution images in `images/`. |
| `sweep-standalone.dc.html` | Standalone variant that references the minified thumbnails in `min/` (declared via `ext-resource-dependency`). |
| `support.js` | The Claude Design **dc‑runtime** (`<x-dc>` / `<sc-if>` / `<sc-for>` / `{{ }}`). It self‑boots on `DOMContentLoaded`, loads React 18 UMD from unpkg, and mounts the app. |
| `images/` | Full‑resolution property photos. |
| `min/` | Minified thumbnails used by the standalone build. |

## Running

The `.dc.html` files reference `./support.js` and local images, so they must be served over HTTP
(not opened with `file://`). The runtime fetches React/ReactDOM/Babel from `unpkg.com`, so an
internet connection is required.

```bash
python3 -m http.server 8099
# then open:
#   http://127.0.0.1:8099/sweep%20sotheby's.dc.html
```

## Notes

- Listings without a usable photo intentionally fall back to the designed **"List Sotheby's /
  LUXURY ESTATES"** brand‑gradient card.
- Four source photos (`748248011r`, `748248012r`, `748248013r`, `754471078r`) could not be
  retrieved in full from the design project (the import API caps file content at 256 KiB and these
  originals exceed it), so their listings use the brand‑gradient fallback. All other photos are
  complete; a few oversized ones were re‑encoded to fit.

## Run with Node

A zero‑dependency Node static server is included:

```bash
npm start          # serves on http://localhost:3000 (PORT env overridable)
```

Routes: `/` and `/standalone` serve the two builds; everything else is served
from disk with correct content types.

## Deploy to Vercel

The repo is a static site, configured by `vercel.json` (`framework: null`, no
build step, output = repo root). On a push, Vercel serves the files directly
from its CDN — `index.html` (a copy of the main app) is served at `/`, so the
deployment URL opens the app immediately. `/standalone` serves the thumbnail
build. No Node process runs on Vercel; `server.js` / `npm start` is for local
use or any Node host (Render, Railway, etc.).
