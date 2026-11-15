"""Build upload-ready WTMLs for the Euclid (AstroPix/ENSCI) feed.

The djangoplicity build_deliverable.py reads AVM metadata.json; AstroPix
candidates carry their text in candidates/<id> instead, and corepipe's AstroPix
processing sets only the title. This fills in the text, the bands and the ids,
absolutizes the URLs and writes:

  processed/<id>/index.wtml   uploaded with the tiles. BandPass is the dominant
                              band (IR), as `cattool emit` writes it for clients;
                              Xbands / Xdominant_band carry the detail.
  euclid.wtml                 (--out) the ingest input: a "Euclid" Folder of the
                              new Places, newest first, BandPass="Multi".

Usage (wwt env, from feeds/euclid):
    python build_euclid.py --out euclid.wtml [--exclude ID ...] ids...
"""
import argparse
import html
import json
import math
import os
import re
import sys
import unicodedata

from wwt_data_formats.enums import Bandpass
from wwt_data_formats.folder import Folder, make_absolutizing_url_mutator
from wwt_data_formats.place import Place

PREFIX = "https://data1.wwtassets.org/feeds/euclid/"
FEED = "euclid"

# Titles that don't say what the object is, or don't say Euclid.
RENAMES = {
    "euclid20240523a": "Euclid’s view of galaxy cluster Abell 2764",
    "euclid20240523b": "Euclid’s view of the Dorado group of galaxies",
    "euclid20240523d": "Euclid’s view of galaxy cluster Abell 2390",
    "euclid20240523e": "Euclid’s view of spiral galaxy NGC 6744",
    "euclid20251105a": "Euclid’s view of dark cloud LDN 1641",
}

# Everything ENSCI publishes is a VIS + NISP colour composite; an image from
# one camera only would go here as {image_id: (bandpass, bands)}.
SINGLE_CAMERA = {}

# ENSCI's AVM positions sit 2-4" north-west of DSS2 (and of the WWT team's own
# placements of the 2023/24 ERO images already in the database). Per-image
# translations measured against DSS2 Red; see astrometry.json for the numbers
# and how they were measured.
_ap = os.path.join(os.path.dirname(os.path.abspath(__file__)), "astrometry.json")
ASTROMETRY = json.load(open(_ap, encoding="utf-8"))["corrections"] if os.path.isfile(_ap) else {}

ARTIFACTS = {
    "bytes-repr": re.compile(r"(^|[\s>\"])b['\"]"),
    "backslash-x": re.compile(r"\\x[0-9a-fA-F]{2}"),
    "double-escape": re.compile(r"&amp;(amp|lt|gt|quot|#\d+);"),
    "replacement-char": re.compile("�"),
    "http-asset": re.compile(r"(Url|Thumbnail|ThumbnailUrl)=?\"?>?http://"),
}


def clean(s):
    if not s:
        return s
    s = html.unescape(s).replace(" ", " ")
    s = unicodedata.normalize("NFC", s)
    s = "\n".join(" ".join(line.split()) for line in s.splitlines())
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def credit(s):
    s = clean(s)
    # ENSCI sometimes appends the licence to the credit line.
    return re.sub(r";\s*CC BY-SA 3\.0 IGO.*$", "", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    entries, log = [], []
    for uid in a.ids:
        rel = os.path.join("processed", uid, "index_rel.wtml")
        if not os.path.isfile(rel):
            log.append(f"SKIP {uid}: no index_rel.wtml")
            continue
        info = json.load(open(os.path.join("candidates", uid), encoding="utf-8"))
        image_id = info["image_id"]
        f = Folder.from_file(rel)
        pl = [c for c in f.children if isinstance(c, Place)][0]
        im = pl.foreground_image_set or pl.image_set
        name = RENAMES.get(image_id) or clean(info["title"])
        pl.name = im.name = f.name = name
        pl.description = clean(info.get("description") or info.get("headline") or "")
        im.credits = credit(info["image_credit"])
        im.credits_url = info["reference_url"]
        fix = ASTROMETRY.get(uid)
        if fix:
            # A few-arcsec translation: move the tangent point (and the Place).
            im.center_x += fix["east_as"] / 3600 / math.cos(math.radians(im.center_y))
            im.center_y += fix["north_as"] / 3600
            pl.ra_hr += fix["east_as"] / 3600 / math.cos(math.radians(pl.dec_deg)) / 15
            pl.dec_deg += fix["north_as"] / 3600
            # Q1 mosaics also need a pixel-scale and a small rotation fix
            # (about the tangent point; Offset[XY] are in degrees, so scale too).
            k = 1 + fix.get("scale", 0.0)
            im.base_degrees_per_tile *= k
            im.offset_x = (im.offset_x or 0.0) * k
            im.offset_y = (im.offset_y or 0.0) * k
            im.rotation_deg += fix.get("rotation_deg", 0.0)
        band, bands = SINGLE_CAMERA.get(image_id, (Bandpass.INFRARED, "Visible,IR"))
        im.band_pass = band
        if "," in bands:
            im.xmeta.bands = bands
            im.xmeta.dominant_band = band.value
        im.xmeta.astropix_ids = f"ensci|{image_id}"
        im.xmeta.corepipe_ids = f"{FEED}|{uid}"
        f.mutate_urls(make_absolutizing_url_mutator(PREFIX + uid + "/"))
        with open(os.path.join("processed", uid, "index.wtml"), "wb") as fh:
            f.write_xml(fh, dest_wants_bytes=True)
        entries.append((info.get("image_release_date") or "", image_id, uid))
        log.append(f"ok   {uid}: {name}")

    merged = Folder()
    merged.name = "Euclid"
    # newest release first; within a release, by id (the full mosaic before its zooms)
    entries.sort(key=lambda e: e[1])
    entries.sort(key=lambda e: e[0], reverse=True)
    for _, _, uid in entries:
        pl = [c for c in Folder.from_file(os.path.join("processed", uid, "index.wtml")).children
              if isinstance(c, Place)][0]
        im = pl.foreground_image_set or pl.image_set
        if getattr(im.xmeta, "bands", None):
            im.band_pass = Bandpass.MULTI  # the database keeps Multi; emit writes the dominant band
        merged.children.append(pl)
    with open(a.out, "wb") as fh:
        merged.write_xml(fh, dest_wants_bytes=True)

    bad = 0
    for path in [a.out] + [os.path.join("processed", u, "index.wtml") for u in a.ids]:
        if not os.path.isfile(path):
            continue
        txt = open(path, encoding="utf-8").read()
        for n, p in ARTIFACTS.items():
            hits = p.findall(txt)
            if hits:
                bad += len(hits)
                log.append(f"ARTIFACT {n} in {path}: {len(hits)}")
    log.append(f"\n{len(merged.children)} places -> {a.out}; artifacts: {bad}")
    sys.stdout.buffer.write(("\n".join(log) + "\n").encode("utf-8"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
