# Shared listings dataset

`data/listings.json` is the **canonical, app-agnostic** dataset of real
properties crawled from **List Sotheby's International Realty Japan**
(https://list-sir.jp/buy/). It is the single source of truth that other
projects in this workspace (e.g. **`../masion-feed`**) consume so every app
shows the same listings and photos.

It is produced by `../tools/crawl-listings.py` (run from the repo root):

```bash
WANT=18 GALLERY=5 python3 tools/crawl-listings.py
```

That command refreshes `data/listings.json`, downloads each property's photos
into `images/` (full-res) and `min/` (560 px thumbnails), and re-splices the two
`.dc.html` builds. **Do not hand-edit the Japan (`sir-*`) listings** — re-run the
crawler.

### Hawaii listings (`hi-*`)

The crawler covers Japan only. **Hawaii** units come from a separate source,
`https://list-hawaii.jp/` (Honolulu / Kakaako — Waiea, Anaha, Kōʻula, ʻAʻaliʻi,
Victoria Place). That site sits behind Cloudflare Turnstile and its `robots.txt`
disallows automated crawlers, so the Hawaii rows are **assembled manually** from
pages opened in a human-cleared browser session, not by the crawler. The source
photos are vendored under `tools/hawaii-mls/` (named `<MLS#>-<n>.jpg`) and copied
into `images/`/`min/` as `hi-<building>-<unit>-<n>.jpg`. To add more, collect the
listing facts + `/matrix/downloaded-images/RESI/<MLS#>/<n>.jpg` photos for each
unit and append `hi-*` objects following the schema below.

## How another agent / app gets this data

Pick whichever fits your project:

1. **Read it in place (same workspace).** Load
   `../masion-sweep/data/listings.json` and reference photos at
   `../masion-sweep/images/<file>` (or `../masion-sweep/min/<file>`). Good for
   local dev where both repos sit side by side.

2. **Vendor a self-contained copy (recommended for separate deploys).** Run the
   share script from the `masion-sweep` repo root:

   ```bash
   python3 tools/share-data.py ../masion-feed
   ```

   It copies `data/listings.json` plus the referenced photos into the target
   repo under `data/` (`data/listings.json`, `data/images/`, `data/min/`) so
   that repo deploys independently (e.g. on Vercel) without reaching across the
   filesystem. Re-run it after every crawl to stay in sync.

3. **Fetch over HTTP.** When `masion-sweep` is running (`npm start`, or its
   Vercel deploy), the file is served as a static asset:

   ```
   GET /data/listings.json
   GET /images/<file>      # full-res
   GET /min/<file>         # thumbnail
   ```

## Schema (`schemaVersion: 1`)

Top-level envelope:

| field | meaning |
| --- | --- |
| `source` | origin site |
| `generatedBy` | the crawler that produced it |
| `imageBase` | `{ full: "images/", thumb: "min/" }` — prefix for the paths below |
| `count` | number of listings |
| `schemaVersion` | bump when the shape changes |
| `listings` | array of listing objects (below) |

Each `listings[]` object:

| field | type | meaning |
| --- | --- | --- |
| `id` | string | stable id, e.g. `sir-4018734` |
| `name` | string | building / property name (JA) |
| `area` | string | full address (JA) |
| `areaUp` | string | uppercased locale line, e.g. `MINATO · TOKYO` |
| `price` | string | formatted price, e.g. `2億9,990万円` |
| `layout` | string | madori · size, e.g. `2LDK ・ 84.74㎡` |
| `img` | string | lead photo path (`images/<file>`) |
| `img2` | string | second photo (falls back to `img`) |
| `gallery` | string[] | **all** photos, full-res (`images/<file>`), 1–5 entries |
| `thumbs` | string[] | same photos as 560 px thumbnails (`min/<file>`) |
| `facts` | [label, value][] | up to 3 spec pairs, e.g. `[["間取り","2LDK"], …]` |
| `tags` | string[] | up to 3 chips (access / 新築 / floors) |
| `summary` | string | lead-photo caption / blurb (JA) |
| `agent` | string | advisor name (JA) |
| `agentTitle` | string | advisor title (JA) |
| `agentReply` | string | typical reply-time note (JA) |

Notes:
- `gallery[0]` always equals `img`; `gallery` excludes floor-plans and shared
  facility shots (exterior + interior only).
- Photos carry List Sotheby's own subtle watermark.
- All text is Japanese source copy; translate downstream if you localize.
