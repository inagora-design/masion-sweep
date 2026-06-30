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
