"""Inventory science.nasa.gov Hubble image assets ("stma" posts) via the WP REST API.

    python nasa_stma.py OUTDIR

Writes OUTDIR/stma.json (raw, id/date/link/title/acf) and OUTDIR/hubble_assets.tsv
with title, date, credit, Kober flag, RA/Dec, size text, instrument, filters,
largest download (WxH, bytes, url).
"""

import ast
import csv
import html
import json
import os
import re
import sys
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; wwt-catalog-inventory)"}
URL = ("https://science.nasa.gov/wp-json/wp/v2/stma?science-org=9369&per_page=100&page={p}"
       "&_fields=id,date,link,title,acf")


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    raw = os.path.join(out, "stma.json")
    if os.path.exists(raw):
        items = json.load(open(raw, encoding="utf-8"))
    else:
        items, p = [], 1
        while True:
            for i in range(4):
                r = requests.get(URL.format(p=p), headers=UA, timeout=120)
                if r.ok or r.status_code == 400:
                    break
                time.sleep(5 * (i + 1))
            if r.status_code == 400 or not r.ok:
                break
            batch = r.json()
            if not batch:
                break
            items += batch
            print(f"page {p}: {len(items)}", flush=True)
            p += 1
            time.sleep(1)
        json.dump(items, open(raw, "w", encoding="utf-8"))
    rows = []
    for x in items:
        a = x.get("acf") or {}
        if not isinstance(a, dict):
            a = {}
        dl = a.get("downloads") or []
        if isinstance(dl, str):
            try:
                dl = ast.literal_eval(dl)
            except Exception:
                dl = []
        best = max((d for d in dl if isinstance(d, dict) and d.get("width")), key=lambda d: int(d["width"]) * int(d["height"] or 1), default={})
        tif = next((d.get("url", "") for d in dl if isinstance(d, dict) and str(d.get("url", "")).lower().endswith((".tif", ".tiff"))), "")
        credit = html.unescape(re.sub(r"<[^>]+>", " ", str(a.get("credits") or "")))
        rows.append({
            "date": x.get("date", "")[:10],
            "title": html.unescape(x.get("title", {}).get("rendered", "")),
            "link": x.get("link", ""),
            "kober": "Kober" in credit,
            "credit": " ".join(credit.split())[:250],
            "ra": a.get("object_right_ascension", ""),
            "dec": a.get("object_declination", ""),
            "size": a.get("object_dimensions", ""),
            "instrument": a.get("data_instrument", ""),
            "filters": a.get("data_filters", ""),
            "w": best.get("width", ""),
            "h": best.get("height", ""),
            "bytes": best.get("size", ""),
            "best_url": best.get("url", ""),
            "tif_url": tif,
        })
    with open(os.path.join(out, "hubble_assets.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} assets; {sum(r['kober'] for r in rows)} credit Kober")


if __name__ == "__main__":
    main()
