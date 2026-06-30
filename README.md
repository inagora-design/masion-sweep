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

## Listings data (live crawl)

The listings are real properties from **List Sotheby's International Realty
Japan** (https://list-sir.jp/buy/), pulled by `tools/crawl-listings.py`.

The `/buy/` page loads its grid from a JSON endpoint
(`GET /api/apiHandller.php?...`); the crawler calls it directly, keeps listings
that have real exterior photos, downloads those photos into `images/` (and
560px thumbnails into `min/`), maps each record into the app's data shape
(`id, name, area, areaUp, price, layout, facts, tags, summary, agent…`), and
rewrites the `this.DATA = [...]` block (plus the deck/threads/popular arrays)
in both `.dc.html` builds.

```bash
WANT=18 GALLERY=5 python3 tools/crawl-listings.py   # refresh listings (needs Pillow)
```

`WANT` sets how many listings to publish; `GALLERY` sets how many photos per
listing (exterior + interior, floor‑plans and shared facility shots excluded).
Each property's full photo set powers a **swipeable gallery** in the detail
sheet (the `gallery` array on each record). Raw downloads are cached under
`tools/.imgcache/` (git‑ignored) so re‑runs don't re‑hit the network. Photos
carry List Sotheby's own subtle watermark.

## Shared dataset (`data/listings.json`)

The crawler also writes a canonical, app‑agnostic dataset to
**`data/listings.json`** — the single source of truth other apps in this
workspace consume (e.g. `../masion-feed`). See **[`data/README.md`](data/README.md)**
for the full schema and the three ways to consume it. To vendor a
self‑contained copy into a sibling repo:

```bash
python3 tools/share-data.py ../masion-feed   # copies listings.json + photos
```

## Run with Node

A single zero‑dependency request handler (`lib/static.js`) backs both local
hosting and the Vercel deploy.

```bash
npm start          # http://localhost:3000  (PORT env overridable)
```

`/` serves the main app, `/standalone` serves the thumbnail build, and every
other path is read from disk with the correct content type.

## Deploy to Vercel (dynamic / Serverless Function)

This is configured as a **dynamic** Vercel deployment, not a plain static
upload:

- `api/index.js` is a Vercel **Node Serverless Function** that wraps the same
  `lib/static.js` handler.
- `vercel.json` rewrites every route (`/(.*)`) to that function, so the Node
  code generates the response for `/` and `/standalone`.
- Rewrites only apply when no static file matches, so real assets
  (`support.js`, `images/`, `min/`, the `.dc.html` files) are still served
  straight from Vercel's CDN — the function only handles the entry routes.
- `includeFiles: "*.dc.html"` bundles the two HTML builds into the function so
  it can read them at request time.

On push, Vercel builds the function and the site is live: opening the
deployment URL runs the Node function, which returns the app (its `support.js`
runtime then loads React 18 from unpkg). The same handler runs locally via
`npm start` and on any other Node host.
