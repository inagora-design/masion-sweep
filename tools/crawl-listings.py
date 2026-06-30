#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawler for List Sotheby's International Realty Japan (https://list-sir.jp/buy/).

The /buy/ page loads its listings from a JSON endpoint:
    GET /api/apiHandller.php?type=multiple&search_type=all&page=N&item_count=12&control=2
Each item carries `value` (raw), `readable` (formatted strings), and `image_info`
(photo categories). This script pulls real listings, downloads their exterior
photos locally, maps each into the app's data shape, and rewrites the
`this.DATA = [...]` block (plus the dependent decks/threads) in both
`sweep sotheby's.dc.html` (images/) and `sweep-standalone.dc.html` (min/).

Network goes through curl (works behind this sandbox's proxy); Pillow handles
image resizing. Re-runnable.
"""
import json, subprocess, sys, os, re, time
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
API = "https://list-sir.jp/api/apiHandller.php"
WANT = int(os.environ.get("WANT", "30"))   # number of listings to publish
GALLERY_MAX = int(os.environ.get("GALLERY", "5"))  # photos per listing (gallery)
MAX_PAGES = int(os.environ.get("MAX_PAGES", "26"))  # scan whole inventory (~1218 / 50)

# Popular-search chips shown in the app (clickable → runs the search).
POPULAR_CHIPS = ["軽井沢", "ニセコ", "葉山", "東京都 港区", "ハワイ"]

# Areas to guarantee from the list-sir.jp crawl so those chips return results;
# (chip label, address-substring to match, min listings to guarantee).
# ハワイ is not on list-sir.jp — it is injected from HAWAII_EXTRA (vendored images).
HOT_AREAS = [
    ("軽井沢",      "軽井沢", 4),
    ("東京都 港区",  "港区",   4),
    ("葉山",        "葉山",   3),
    ("ニセコ",      "ニセコ", 3),
]

# Hawaii listings (List Sotheby's Waiea, Honolulu) — photos vendored in
# tools/hawaii/ because list-hawaii.jp is bot-protected. Source data supplied by
# the user (MAISON design export). area contains "ハワイ" so search matches.
HAWAII_EXTRA = [
    {"id": "hi-waiea-2903", "name": "Waiea 1118 アラモアナ #2903",
     "area": "米国 ハワイ ホノルル カカアコ", "areaUp": "HONOLULU · HAWAII",
     "price": "9億8,000万円", "layout": "3BR ・ 200㎡",
     "facts": [["間取り", "3BR"], ["専有面積", "200㎡"], ["築年", "2016年"]],
     "tags": ["アラモアナセンター 近接", "オーシャンビュー", "コンシェルジュ"],
     "summary": "カカアコの名門レジデンスWaiea、29階のオーシャンビュー邸。",
     "agent": "佐藤 健一", "agentTitle": "インターナショナル アドバイザー",
     "agentReply": "通常1時間以内に返信",
     "_src": ["waiea-2903-1.jpg", "waiea-2903-2.jpg"]},
    {"id": "hi-waiea-3401", "name": "Waiea 1118 アラモアナ #3401",
     "area": "米国 ハワイ ホノルル カカアコ", "areaUp": "HONOLULU · HAWAII",
     "price": "12億8,000万円", "layout": "3BR ・ 230㎡",
     "facts": [["間取り", "3BR"], ["専有面積", "230㎡"], ["築年", "2016年"]],
     "tags": ["ダイヤモンドヘッド眺望", "オーシャンビュー", "最上級"],
     "summary": "Waiea 34階、ダイヤモンドヘッドと太平洋を見渡す最上級邸。",
     "agent": "佐藤 健一", "agentTitle": "インターナショナル アドバイザー",
     "agentReply": "通常1時間以内に返信",
     "_src": ["waiea-3401-1.jpg", "waiea-3401-2.jpg"]},
]

PREF = {
 "北海道":"HOKKAIDO","青森県":"AOMORI","岩手県":"IWATE","宮城県":"MIYAGI","秋田県":"AKITA",
 "山形県":"YAMAGATA","福島県":"FUKUSHIMA","茨城県":"IBARAKI","栃木県":"TOCHIGI","群馬県":"GUNMA",
 "埼玉県":"SAITAMA","千葉県":"CHIBA","東京都":"TOKYO","神奈川県":"KANAGAWA","新潟県":"NIIGATA",
 "富山県":"TOYAMA","石川県":"ISHIKAWA","福井県":"FUKUI","山梨県":"YAMANASHI","長野県":"NAGANO",
 "岐阜県":"GIFU","静岡県":"SHIZUOKA","愛知県":"AICHI","三重県":"MIE","滋賀県":"SHIGA",
 "京都府":"KYOTO","大阪府":"OSAKA","兵庫県":"HYOGO","奈良県":"NARA","和歌山県":"WAKAYAMA",
 "鳥取県":"TOTTORI","島根県":"SHIMANE","岡山県":"OKAYAMA","広島県":"HIROSHIMA","山口県":"YAMAGUCHI",
 "徳島県":"TOKUSHIMA","香川県":"KAGAWA","愛媛県":"EHIME","高知県":"KOCHI","福岡県":"FUKUOKA",
 "佐賀県":"SAGA","長崎県":"NAGASAKI","熊本県":"KUMAMOTO","大分県":"OITA","宮崎県":"MIYAZAKI",
 "鹿児島県":"KAGOSHIMA","沖縄県":"OKINAWA",
}
CITY = {
 "新宿区":"SHINJUKU","港区":"MINATO","渋谷区":"SHIBUYA","千代田区":"CHIYODA","中央区":"CHUO",
 "目黒区":"MEGURO","世田谷区":"SETAGAYA","品川区":"SHINAGAWA","文京区":"BUNKYO","台東区":"TAITO",
 "江東区":"KOTO","大田区":"OTA","杉並区":"SUGINAMI","豊島区":"TOSHIMA","中野区":"NAKANO",
 "練馬区":"NERIMA","板橋区":"ITABASHI","北区":"KITA","荒川区":"ARAKAWA","足立区":"ADACHI",
 "葛飾区":"KATSUSHIKA","江戸川区":"EDOGAWA","墨田区":"SUMIDA",
 "横浜市":"YOKOHAMA","鎌倉市":"KAMAKURA","藤沢市":"FUJISAWA","逗子市":"ZUSHI","葉山町":"HAYAMA",
 "軽井沢町":"KARUIZAWA","ニセコ町":"NISEKO","倶知安町":"KUTCHAN","恩納村":"ONNA","今帰仁村":"NAKIJIN","北谷町":"CHATAN",
 "軽井沢町":"KARUIZAWA","箱根町":"HAKONE","熱海市":"ATAMI","京都市":"KYOTO","大阪市":"OSAKA",
 "福岡市":"FUKUOKA","札幌市":"SAPPORO","那覇市":"NAHA","ニセコ町":"NISEKO","つくば市":"TSUKUBA",
}
AGENTS = [
 ("浦田 美和","インターナショナル アドバイザー","通常1時間以内に返信"),
 ("志水 銀太","プロパティ アドバイザー","通常2時間以内に返信"),
 ("安井 弥月","リゾート プロパティ アドバイザー","通常1時間以内に返信"),
 ("宮本 渉","プロパティ アドバイザー","通常1時間以内に返信"),
 ("大嶋 諒太","プロパティ アドバイザー","通常2時間以内に返信"),
 ("髙野 友紀子","インターナショナル アドバイザー","通常1時間以内に返信"),
]


def _safe_loads(s):
    """list-sir.jp sometimes emits invalid JSON escapes (e.g. a bare \\u with
    fewer than 4 hex digits) in free-text fields. Double any backslash that
    doesn't start a valid JSON escape so json.loads can parse the page."""
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        fixed = re.sub(r'\\(?=u(?![0-9a-fA-F]{4})|[^"\\/bfnrtu])', r'\\\\', s)
        return json.loads(fixed)


def curl_json(url):
    p = subprocess.run(
        ["curl", "-s", "--max-time", "45", "-A", UA,
         "-H", "X-Requested-With: XMLHttpRequest",
         "-H", "Accept: application/json, text/javascript, */*; q=0.01",
         "-H", "Referer: https://list-sir.jp/buy/", url],
        capture_output=True)
    return _safe_loads(p.stdout.decode("utf-8", "replace"))


def curl_download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1024:
        return True   # cached
    subprocess.run(["curl", "-s", "--max-time", "60", "-A", UA,
                    "-H", "Referer: https://list-sir.jp/", "-o", dest, url], check=False)
    return os.path.exists(dest) and os.path.getsize(dest) > 1024


def img_url(images, no):
    if no is None:
        return None
    e = images.get(str(no))
    if not e:
        return None
    p = (e.get("img_full_path") or "").strip()
    if not p:
        return None
    return "https:" + p if p.startswith("//") else p


def usable_photos(item):
    """Ordered real photo URLs, excluding floor-plans and facility shots."""
    v = item["value"]; info = item.get("image_info") or {}
    cat = info.get("category") or {}
    images = v.get("images") or {}
    madori = cat.get("madori")
    skip = set(cat.get("shisetsu") or [])
    order = info.get("sort") or list(images.keys())
    urls = []
    for no in order:
        try:
            n = int(no)
        except (TypeError, ValueError):
            n = no
        if n == madori or n in skip:
            continue
        u = img_url(images, n)
        if u and u not in urls:
            urls.append(u)
    return urls


def pretty_price(v):
    p = v.get("price")
    if not p:
        return (item_readable_price(v) or "価格応談")
    p = int(p)  # in 万円
    if p >= 10000:
        oku, man = divmod(p, 10000)
        return f"{oku}億{man:,}万円" if man else f"{oku}億円"
    return f"{p:,}万円"


def item_readable_price(v):
    return None


def area_up(r):
    pref = PREF.get(r.get("pref_name", ""), None)
    city = CITY.get(r.get("shiku_name", ""), None)
    if city and pref:
        return f"{city} · {pref}"
    if pref:
        return f"{pref} · JAPAN"
    return "JAPAN"


def menseki(r, v):
    for k, label in (("tatesen_menseki", "専有面積"),
                     ("taten_menseki", "建物面積"),
                     ("tochi_menseki", "土地面積")):
        s = r.get(k)
        if s and s != "-":
            return label, s
    return "面積", "-"


def madori_str(r, v):
    room = r.get("madori_room_su")
    kbn = r.get("madori_kbn") or ""
    if room and room != "-" and kbn:
        return f"{room}{kbn}"
    return None


def access_str(r, v):
    # readable.* already include their units (e.g. "新宿御苑前駅", "4分")
    ek = (r.get("eki_name_1") or "").strip()
    wt = str(r.get("walk_time_1") or "").strip()
    if ek and wt and wt not in ("-", "None"):
        return f"{ek} 徒歩{wt}"
    return ek or None


def build_listing(item, idx):
    v, r = item["value"], item["readable"]
    photos = usable_photos(item)
    if not photos:
        return None
    bk = v.get("bk_id") or v.get("bk_cd") or str(idx)
    lid = "sir-" + re.sub(r"[^0-9A-Za-z]+", "", str(bk))
    name = (r.get("view_tatemono_name") or r.get("tatemono_name") or "List Sotheby's 物件").strip()
    address = (r.get("address") or f"{r.get('pref_name','')}{r.get('shiku_name','')}").strip()
    mad = madori_str(r, v)
    mlabel, msize = menseki(r, v)
    layout = f"{mad} ・ {msize}" if mad else msize
    # facts
    facts = []
    if mad:
        facts.append(["間取り", mad])
    facts.append([mlabel, msize])
    floor = r.get("shozai_kai")
    if floor and floor != "-":
        facts.append(["所在階", floor])
    elif r.get("chiku_ymd") and r.get("chiku_ymd") != "-":
        facts.append(["築年月", r.get("chiku_ymd")])
    facts = facts[:3]
    # tags
    tags = []
    acc = access_str(r, v)
    if acc:
        tags.append(acc)
    if r.get("shinchiku_flg"):
        tags.append(r["shinchiku_flg"])              # 新築 / 中古
    if r.get("chijo_kai") and r["chijo_kai"] != "-":
        tags.append(str(r["chijo_kai"]))
    tags = [t for t in tags if t][:3]
    # summary: prefer the lead photo's caption
    summary = ""
    for no in (item.get("image_info", {}).get("sort") or []):
        e = (v.get("images") or {}).get(str(no))
        if e and (e.get("img_com") or e.get("img_title")):
            c = (e.get("img_com") or e.get("img_title")).strip()
            if c and c not in ("-",) and "間取" not in (e.get("img_sbt_kbn") or ""):
                summary = c
                break
    if not summary:
        summary = f"{address}に位置する{name}。"
    agent, atitle, areply = AGENTS[idx % len(AGENTS)]
    return {
        "id": lid, "name": name, "area": address, "areaUp": area_up(r),
        "price": pretty_price(v), "layout": layout,
        "facts": facts, "tags": tags, "summary": summary,
        "agent": agent, "agentTitle": atitle, "agentReply": areply,
        "_photos": photos[:GALLERY_MAX],
    }


def process_image(src, dst, maxw, q):
    try:
        with Image.open(src) as im:
            im.load()
            if im.mode != "RGB":
                im = im.convert("RGB")
            if im.width > maxw:
                h = round(im.height * maxw / im.width)
                im = im.resize((maxw, h), Image.LANCZOS)
            im.save(dst, "JPEG", quality=q, optimize=True, progressive=True)
        return True
    except Exception as e:
        print("  ! image error", dst, e)
        return False


def write_dataset(listings):
    """Write the canonical dataset to data/listings.json.

    This is the portable, app-agnostic representation other projects consume.
    Image paths are repo-relative (`images/<file>` full-res, `min/<file>`
    thumbnail — same basename). Internal scratch keys are stripped.
    """
    out = []
    for L in listings:
        gallery = list(L.get("gallery") or [])
        out.append({
            "id": L["id"],
            "name": L["name"],
            "area": L["area"],
            "areaUp": L["areaUp"],
            "price": L["price"],
            "layout": L["layout"],
            "img": L["img"],
            "img2": L["img2"],
            "gallery": gallery,                              # full-res, images/<file>
            "thumbs": [g.replace("images/", "min/") for g in gallery],
            "facts": L["facts"],
            "tags": L["tags"],
            "summary": L["summary"],
            "agent": L["agent"],
            "agentTitle": L["agentTitle"],
            "agentReply": L["agentReply"],
        })
    doc = {
        "source": "https://list-sir.jp/buy/  (List Sotheby's International Realty Japan)",
        "generatedBy": "masion-sweep/tools/crawl-listings.py",
        "note": "Real listings crawled from List Sotheby's. Photos carry their watermark.",
        "imageBase": {"full": "images/", "thumb": "min/"},
        "count": len(out),
        "schemaVersion": 1,
        "listings": out,
    }
    ddir = os.path.join(ROOT, "data")
    os.makedirs(ddir, exist_ok=True)
    path = os.path.join(ddir, "listings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  wrote data/listings.json ({len(out)} listings)")


def _blob(item):
    r = item.get("readable") or {}
    return (r.get("pref_name", "") + r.get("shiku_name", "") + (r.get("address") or ""))


def main():
    print(f"Fetching listings from {API} ...")
    # 1) Scan the inventory and keep every candidate that has real photos.
    candidates, seen_bk, page = [], set(), 1
    while page <= MAX_PAGES:
        url = f"{API}?type=multiple&search_type=all&search_sort=&page={page}&item_count=50&control=2"
        try:
            d = curl_json(url)
        except Exception as e:
            print("  page", page, "parse error (skipped):", str(e)[:50]); page += 1; continue
        data = d.get("data") or []
        if not data:
            break
        kept = 0
        for item in data:
            v = item.get("value") or {}
            bk = v.get("bk_id") or v.get("bk_cd")
            if not bk or bk in seen_bk or not usable_photos(item):
                continue
            seen_bk.add(bk); candidates.append(item); kept += 1
        print(f"  page {page}: {len(data)} items, +{kept} (total {d.get('totalCount')})")
        if len(data) < 50:
            break
        page += 1
        time.sleep(0.2)
    print(f"Collected {len(candidates)} candidates with real photos.")

    # 2) Select: first guarantee the popular-area quotas, then fill to WANT.
    chosen, chosen_bk = [], set()

    def take(item):
        v = item.get("value") or {}
        bk = v.get("bk_id") or v.get("bk_cd")
        if bk in chosen_bk:
            return False
        chosen_bk.add(bk); chosen.append(item); return True

    for chip, match, quota in HOT_AREAS:
        cnt = 0
        for item in candidates:
            if cnt >= quota:
                break
            if match in _blob(item) and take(item):
                cnt += 1
        print(f"  hot '{chip}': {cnt}/{quota}")
    for item in candidates:
        if len(chosen) >= WANT:
            break
        take(item)

    # 3) Build listing objects (agent rotates by index).
    listings, seen = [], set()
    for item in chosen:
        L = build_listing(item, len(listings))
        if L and L["id"] not in seen:
            seen.add(L["id"]); listings.append(L)

    print(f"Selected {len(listings)} listings with real photos.")
    os.makedirs(os.path.join(ROOT, "images"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "min"), exist_ok=True)

    # remove previous listing images (keep nothing stale)
    for d in ("images", "min"):
        for f in os.listdir(os.path.join(ROOT, d)):
            os.remove(os.path.join(ROOT, d, f))

    tmp = os.path.join(ROOT, "tools", ".imgcache")
    os.makedirs(tmp, exist_ok=True)
    for L in listings:
        locs = []
        for n, purl in enumerate(L["_photos"], 1):
            raw = os.path.join(tmp, f"{L['id']}-{n}.bin")
            ok = curl_download(purl, raw)
            if not ok:
                continue
            rel = f"{L['id']}-{n}.jpg"
            if process_image(raw, os.path.join(ROOT, "images", rel), 1280, 82):
                process_image(raw, os.path.join(ROOT, "min", rel), 560, 80)
                locs.append(rel)
            time.sleep(0.2)
        L["gallery"] = [f"images/{x}" for x in locs]
        L["img"] = f"images/{locs[0]}" if locs else None
        L["img2"] = f"images/{locs[1]}" if len(locs) > 1 else (f"images/{locs[0]}" if locs else None)
        print(f"  {L['id']:<18} {len(locs)} photo(s)  {L['name'][:24]}")
    listings = [L for L in listings if L["img"]]
    print(f"{len(listings)} listings have downloaded photos.")

    # ---- inject Hawaii listings (vendored photos, not on list-sir.jp) ----
    hwdir = os.path.join(ROOT, "tools", "hawaii")
    for H in HAWAII_EXTRA:
        locs = []
        for n, src in enumerate(H["_src"], 1):
            srcpath = os.path.join(hwdir, src)
            if not os.path.exists(srcpath):
                continue
            rel = f"{H['id']}-{n}.jpg"
            if process_image(srcpath, os.path.join(ROOT, "images", rel), 1280, 82):
                process_image(srcpath, os.path.join(ROOT, "min", rel), 560, 80)
                locs.append(rel)
        if not locs:
            print(f"  ! Hawaii {H['id']}: no images found in tools/hawaii/"); continue
        rec = {k: v for k, v in H.items() if k != "_src"}
        rec["gallery"] = [f"images/{x}" for x in locs]
        rec["img"] = f"images/{locs[0]}"
        rec["img2"] = f"images/{locs[1]}" if len(locs) > 1 else f"images/{locs[0]}"
        listings.append(rec)
        print(f"  {H['id']:<18} {len(locs)} photo(s)  {H['name'][:24]}  (Hawaii)")
    print(f"{len(listings)} listings total (incl. Hawaii).")

    # ---- emit canonical machine-readable dataset (data/listings.json) ----
    # This is the source of truth other apps (e.g. ../masion-feed) consume.
    write_dataset(listings)

    # ---- emit JS ----
    def esc(s):
        return json.dumps(s, ensure_ascii=False)

    def data_block(prefix):
        lines = ["    this.DATA = ["]
        for L in listings:
            img = ("null" if not L["img"] else esc(L["img"].replace("images/", prefix)))
            img2 = ("null" if not L["img2"] else esc(L["img2"].replace("images/", prefix)))
            gallery = "[" + ",".join(esc(g.replace("images/", prefix)) for g in L.get("gallery", [])) + "]"
            facts = "[" + ",".join("[" + esc(a) + "," + esc(b) + "]" for a, b in L["facts"]) + "]"
            tags = "[" + ",".join(esc(t) for t in L["tags"]) + "]"
            lines.append(
                "      { id:%s, name:%s, area:%s, areaUp:%s,\n"
                "        price:%s, layout:%s, img:%s, img2:%s,\n"
                "        gallery:%s,\n"
                "        facts:%s,\n        tags:%s,\n        summary:%s,\n"
                "        agent:%s, agentTitle:%s, agentReply:%s }," % (
                    esc(L["id"]), esc(L["name"]), esc(L["area"]), esc(L["areaUp"]),
                    esc(L["price"]), esc(L["layout"]), img, img2,
                    gallery,
                    facts, tags, esc(L["summary"]),
                    esc(L["agent"]), esc(L["agentTitle"]), esc(L["agentReply"])))
        lines.append("    ];")
        ids = [L["id"] for L in listings]
        viewed = ids[1:5]
        reco = ids[5:8]
        threads = ids[:3]
        msgs = ["内見のご希望日をお知らせください。", "資料を送付いたしました。ご確認ください。", "オンライン相談も承っております。"]
        times = ["14:20", "昨日", "月曜"]
        unread = ["true", "true", "false"]
        lines.append("    this.DECK_EXCLUDE = new Set([]);")
        lines.append("    this.DECK = this.DATA.filter(d => !this.DECK_EXCLUDE.has(d.id));")
        lines.append("    this.VIEWED = [" + ",".join(esc(i) for i in viewed) + "];")
        lines.append("    this.RECO   = [" + ",".join(esc(i) for i in reco) + "];")
        lines.append("    this.THREADS = [")
        for k, tid in enumerate(threads):
            lines.append("      { id:%s, last:%s, time:%s, unread:%s }," % (
                esc(tid), esc(msgs[k]), esc(times[k]), unread[k]))
        lines.append("    ];")
        # POPULAR: clickable hot-search chips — every one has real inventory
        lines.append("    this.POPULAR = [" + ",".join(esc(p) for p in POPULAR_CHIPS) + "];")
        return "\n".join(lines) + "\n    "

    def splice(path, prefix):
        with open(path, encoding="utf-8") as f:
            html = f.read()
        a = html.index("    this.DATA = [")
        b = html.index("    this.AICHIPS")
        html = html[:a] + data_block(prefix) + html[b:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print("  spliced", os.path.basename(path))

    splice(os.path.join(ROOT, "sweep sotheby's.dc.html"), "images/")
    splice(os.path.join(ROOT, "sweep-standalone.dc.html"), "min/")

    # rebuild the standalone's ext-resource-dependency meta block
    sp = os.path.join(ROOT, "sweep-standalone.dc.html")
    with open(sp, encoding="utf-8") as f:
        html = f.read()
    metas = []
    for f in sorted(os.listdir(os.path.join(ROOT, "min"))):
        rid = re.sub(r"[^0-9A-Za-z]+", "_", f)
        metas.append(f'<meta name="ext-resource-dependency" content="min/{f}" data-resource-id="{rid}" />')
    block = "\n".join(metas)
    html = re.sub(r'(\n)?<meta name="ext-resource-dependency"[^>]*/>(\s*<meta name="ext-resource-dependency"[^>]*/>)*',
                  "\n" + block, html, count=1)
    with open(sp, "w", encoding="utf-8") as f:
        f.write(html)
    print("  rebuilt standalone resource-dependency metas:", len(metas))

    # keep tools/.imgcache so re-runs don't re-download (git-ignored)
    print("Done.")


if __name__ == "__main__":
    main()
