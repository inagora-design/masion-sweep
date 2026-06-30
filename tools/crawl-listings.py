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
WANT = int(os.environ.get("WANT", "18"))   # number of listings to publish
MAX_PAGES = 8

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
 "横浜市":"YOKOHAMA","鎌倉市":"KAMAKURA","藤沢市":"FUJISAWA","逗子市":"ZUSHI",
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


def curl_json(url):
    p = subprocess.run(
        ["curl", "-s", "--max-time", "45", "-A", UA,
         "-H", "X-Requested-With: XMLHttpRequest",
         "-H", "Accept: application/json, text/javascript, */*; q=0.01",
         "-H", "Referer: https://list-sir.jp/buy/", url],
        capture_output=True)
    return json.loads(p.stdout.decode("utf-8", "replace"))


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
        "_photos": photos[:2],
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


def main():
    print(f"Fetching listings from {API} ...")
    listings, page = [], 1
    seen = set()
    while len(listings) < WANT and page <= MAX_PAGES:
        url = f"{API}?type=multiple&search_type=all&search_sort=&page={page}&item_count=12&control=2"
        try:
            d = curl_json(url)
        except Exception as e:
            print("  page", page, "fetch error:", e); break
        data = d.get("data") or []
        print(f"  page {page}: {len(data)} items (total {d.get('totalCount')})")
        if not data:
            break
        for i, item in enumerate(data):
            L = build_listing(item, len(listings))
            if L and L["id"] not in seen:
                seen.add(L["id"]); listings.append(L)
                if len(listings) >= WANT:
                    break
        page += 1
        time.sleep(0.3)

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
        L["img"] = f"images/{locs[0]}" if locs else None
        L["img2"] = f"images/{locs[1]}" if len(locs) > 1 else (f"images/{locs[0]}" if locs else None)
        print(f"  {L['id']:<18} {len(locs)} photo(s)  {L['name'][:24]}")
    listings = [L for L in listings if L["img"]]
    print(f"{len(listings)} listings have downloaded photos.")

    # ---- emit JS ----
    def esc(s):
        return json.dumps(s, ensure_ascii=False)

    def data_block(prefix):
        lines = ["    this.DATA = ["]
        for L in listings:
            img = ("null" if not L["img"] else esc(L["img"].replace("images/", prefix)))
            img2 = ("null" if not L["img2"] else esc(L["img2"].replace("images/", prefix)))
            facts = "[" + ",".join("[" + esc(a) + "," + esc(b) + "]" for a, b in L["facts"]) + "]"
            tags = "[" + ",".join(esc(t) for t in L["tags"]) + "]"
            lines.append(
                "      { id:%s, name:%s, area:%s, areaUp:%s,\n"
                "        price:%s, layout:%s, img:%s, img2:%s,\n"
                "        facts:%s,\n        tags:%s,\n        summary:%s,\n"
                "        agent:%s, agentTitle:%s, agentReply:%s }," % (
                    esc(L["id"]), esc(L["name"]), esc(L["area"]), esc(L["areaUp"]),
                    esc(L["price"]), esc(L["layout"]), img, img2,
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
        # POPULAR: real JP area names present in the data
        pops = []
        for L in listings:
            c = L["area"]
            for key in CITY:
                if key in c and key not in pops:
                    pops.append(key)
        pops = pops[:6] or ["東京", "神奈川", "京都", "大阪", "軽井沢", "沖縄"]
        lines.append("    this.POPULAR = [" + ",".join(esc(p) for p in pops) + "];")
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
