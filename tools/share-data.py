#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vendor the crawled dataset into a consumer repo so it can deploy independently.

Usage (from the masion-sweep repo root):
    python3 tools/share-data.py ../masion-feed [../another-consumer ...]

For each target it writes a self-contained copy under <target>/data/:
    <target>/data/listings.json   (canonical dataset)
    <target>/data/images/<file>   (full-res photos referenced by the dataset)
    <target>/data/min/<file>      (560px thumbnails)
    <target>/data/README.md       (the consumer doc)

Only photos actually referenced by listings.json are copied. Re-run after every
crawl to keep consumers in sync. Idempotent.
"""
import json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "listings.json")


def referenced_files(doc):
    full, thumb = set(), set()
    for L in doc.get("listings", []):
        for g in (L.get("gallery") or []):
            full.add(os.path.basename(g))
        for t in (L.get("thumbs") or []):
            thumb.add(os.path.basename(t))
        for k in ("img", "img2"):
            if L.get(k):
                full.add(os.path.basename(L[k]))
    return full, thumb


def copy_into(target):
    if not os.path.isdir(target):
        print(f"  ! target not found: {target}")
        return False
    with open(DATA, encoding="utf-8") as f:
        doc = json.load(f)
    full, thumb = referenced_files(doc)

    ddir = os.path.join(target, "data")
    os.makedirs(os.path.join(ddir, "images"), exist_ok=True)
    os.makedirs(os.path.join(ddir, "min"), exist_ok=True)

    shutil.copy2(DATA, os.path.join(ddir, "listings.json"))
    doc_md = os.path.join(ROOT, "data", "README.md")
    if os.path.exists(doc_md):
        shutil.copy2(doc_md, os.path.join(ddir, "README.md"))

    n = 0
    for name in sorted(full):
        src = os.path.join(ROOT, "images", name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(ddir, "images", name)); n += 1
    m = 0
    for name in sorted(thumb):
        src = os.path.join(ROOT, "min", name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(ddir, "min", name)); m += 1

    print(f"  {target}/data: listings.json + {n} images + {m} thumbs")
    return True


def main():
    targets = sys.argv[1:] or ["../masion-feed"]
    if not os.path.exists(DATA):
        sys.exit("data/listings.json missing — run tools/crawl-listings.py first.")
    print("Sharing dataset to:", ", ".join(targets))
    ok = all(copy_into(os.path.abspath(t)) for t in targets)
    print("Done." if ok else "Done (with warnings).")


if __name__ == "__main__":
    main()
