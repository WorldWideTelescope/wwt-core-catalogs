"""Choose a BandPass for a new feed image from its AVM metadata.

`propose_bandpass.py` works from what the catalogue already holds (title,
credits, publisher, collection). A djangoplicity feed image (ESA/Hubble,
ESA/Webb, ESO, NOIRLab) also has AVM spectral metadata: one Facility,
Instrument and Spectral.Band per exposure. This script uses both:

  * The AVM says which telescopes contributed and in which bands. Hubble's own
    exposures give IR when they are all infrared (WFC3/IR, NICMOS),
    Ultraviolet when they are all ultraviolet, and Visible otherwise.
  * A partner telescope in another band (Webb, Chandra, ALMA, Spitzer, GALEX
    ...) makes the image a composite: BandPass="Multi", Xbands = every band
    short to long, Xdominant_band = the partner's band (the first non-visible
    one when there are several), as propose_bandpass.py picks it.
  * Ground-based optical partners (VLT, Subaru, amateur data) stay Visible.
  * propose_bandpass.decide() is run on the title and credits too. When the two
    disagree the line is flagged REVIEW and the AVM answer is used.

Usage (wwt env python):
    python bandpass/band_for_avm.py <feed_dir> [ids...]          # report only
    python bandpass/band_for_avm.py <feed_dir> --csv OUT.csv [ids...]
    python bandpass/band_for_avm.py <feed_dir> --apply WTML [WTML ...]
        set BandPass / Xbands / Xdominant_band on every ImageSet in those
        WTMLs whose CreditsUrl is .../images/<id>/

AVM is read from <feed>/cache_*/<id>/metadata.json, else <feed>/_triage/<id>.json.
With no ids, every id that has AVM is reported.
"""

import argparse
import ast
import csv
import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import propose_bandpass as pb  # noqa: E402

ORDER = pb.ORDER

AVM_BAND = [
    (re.compile(r"gamma", re.I), "Gamma"),
    (re.compile(r"x-?ray", re.I), "XRay"),
    (re.compile(r"ultraviolet|\buv\b", re.I), "Ultraviolet"),
    (re.compile(r"optical|visible", re.I), "Visible"),
    (re.compile(r"infrared|\bir\b", re.I), "IR"),
    (re.compile(r"microwave", re.I), "Microwave"),
    (re.compile(r"radio|millimet", re.I), "Radio"),
]

# Facility names in AVM -> a label from propose_bandpass.TELESCOPES, or
# "Hubble" for Hubble itself. Anything matching no fixed-band telescope counts
# as an optical (variable-band) partner.
HUBBLE = re.compile(r"hubble|\bhst\b", re.I)


def debyte(s):
    if isinstance(s, str) and s[:2] in ("b'", 'b"'):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, (bytes, bytearray)):
                return v.decode("utf-8")
        except Exception:
            pass
    return s


def clean(s):
    return html.unescape(debyte(s or "") or "").strip()


def load_avm(feed, uid):
    for sub in ("cache_done", "cache_todo", "cache_failed", "_hold_large"):
        p = os.path.join(feed, sub, uid, "metadata.json")
        if os.path.isfile(p):
            return json.load(open(p, encoding="utf-8"))
    p = os.path.join(feed, "_triage", uid + ".json")
    if os.path.isfile(p):
        return json.load(open(p, encoding="utf-8"))
    return None


def avm_band(s):
    for rx, b in AVM_BAND:
        if s and rx.search(s):
            return b
    return None


def fixed_label(facility):
    """The propose_bandpass label of a fixed-band telescope, or None."""
    for lab, bands, fixed, rx in pb.TEL_RE:
        if fixed and rx.search(facility):
            return lab
    return None


def sort_bands(bands):
    return pb.sort_bands(bands)


def hubble_band(label, inst, wavelength):
    """One Hubble exposure's band. The central wavelength decides when given:
    ESA labels F814W/F850LP "Infrared" and F336W "Optical", but only the IR
    channel (WFC3/IR, NICMOS: >= 950 nm) makes an infrared image, and F336W and
    bluer filters are ultraviolet."""
    try:
        nm = float(str(wavelength).strip())
    except (TypeError, ValueError):
        nm = None
    if nm:
        if nm < 380:
            return "Ultraviolet"
        if nm >= 950:
            return "IR"
        return "Visible"
    if re.search(r"nicmos|wfc3[/ -]?ir", inst, re.I):
        return "IR"
    return label


def from_avm(info):
    """(bands set, dominant, why) from the AVM exposure list, or None."""
    facs = info.get("Facility") or []
    insts = info.get("Instrument") or []
    sbands = info.get("Spectral.Band") or []
    waves = info.get("Spectral.CentralWavelength") or []
    title = clean(info.get("Title"))
    n = max(len(facs), len(sbands))
    if not n:
        return None
    hubble, partner_bands, partners, unknown = set(), set(), [], 0
    for i in range(n):
        fac = str(facs[i]) if i < len(facs) and facs[i] else ""
        inst = str(insts[i]) if i < len(insts) and insts[i] else ""
        band = avm_band(str(sbands[i])) if i < len(sbands) and sbands[i] else None
        if not fac and not band:
            continue
        if not fac or HUBBLE.search(fac):
            hb = hubble_band(band, inst, waves[i] if i < len(waves) else None)
            if hb:
                hubble.add(hb)
            else:
                unknown += 1
            continue
        lab = fixed_label(fac + " " + inst)
        if lab:
            tb, _ = pb.TEL_BY_LABEL[lab]
            # A fixed telescope's own band list is the truth (Euclid: Visible+IR);
            # an AVM band inside it narrows it.
            b = {band} if band in tb else tb
            partner_bands |= b
            partners.append(lab)
        else:
            # A ground-based or otherwise variable telescope (VLT, DECam, SDSS
            # ...) counts as infrared only through an infrared instrument: its
            # "Infrared" i/z exposures are optical data. Otherwise it adds
            # nothing to Hubble's Visible.
            if pb.IR_INSTRUMENTS.search(inst + " " + fac):
                partner_bands.add("IR")
                partners.append(fac)
    if not hubble and unknown:
        hubble.add("Visible")
    if not hubble and not partner_bands:
        return None

    # Hubble's own contribution: IR when every exposure is infrared,
    # Ultraviolet when every one is ultraviolet, else Visible (a Hubble image
    # mixing UV/IR with optical, or UV with IR, is Hubble's "Visible" view;
    # only a partner telescope in another band makes a composite).
    if len(hubble) == 1:
        hb = set(hubble)
    elif hubble:
        hb = {"Visible"}
        # ...unless the title names one of its bands ("Cosmic Fireworks in
        # Ultraviolet"): a band named in the title wins, as in propose_bandpass.
        named = {b for b, rx in pb.BAND_WORDS if rx.search(title)} & hubble
        if len(named) == 1 and not partner_bands:
            hb = named
    else:
        hb = set()
    bands = hb | partner_bands
    why = f"AVM Hubble={'+'.join(sort_bands(hubble)) or '-'}"
    if partners:
        why += f"; partners={','.join(dict.fromkeys(partners))}->{'+'.join(sort_bands(partner_bands))}"
    comps = sort_bands(bands)
    if len(comps) == 1:
        return set(comps), comps[0], why
    pnv = [b for b in sort_bands(partner_bands) if b != "Visible"]
    dominant = pnv[0] if pnv else next((b for b in comps if b != "Visible"), comps[0])
    return set(comps), dominant, why


def assign(uid, info):
    title, credit, desc = clean(info.get("Title")), clean(info.get("Credit")), clean(info.get("Description"))
    s = {"url": "", "name": title, "current": "Visible", "projection": "Tan", "astropix": "",
         "corepipe": f"hst|{uid}", "credits": credit, "credits_url": info.get("ReferenceURL", ""),
         "description": desc}
    d = pb.decide(s, [], set())
    rule_comps = d["components"].split("+")
    a = from_avm(info)
    if a is None:
        comps, dominant, why, src = rule_comps, d["dominant"], d["evidence"], "rules"
    else:
        comps, dominant, why = sort_bands(a[0]), a[1], a[2]
        src = "avm"
    proposed = comps[0] if len(comps) == 1 else "Multi"
    flag = ""
    if a is not None and set(rule_comps) != set(comps):
        flag = f"REVIEW rules say {'+'.join(rule_comps)} ({d['evidence']})"
    return {
        "id": uid, "title": title, "bandpass": proposed,
        "bands": ",".join(comps) if proposed == "Multi" else "",
        "dominant": dominant if proposed == "Multi" else "",
        "source": src, "why": why, "flag": flag,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feed_dir")
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--csv")
    ap.add_argument("--apply", nargs="+", metavar="WTML")
    a = ap.parse_args()
    feed = os.path.abspath(a.feed_dir)

    if a.apply:
        from wwt_data_formats.enums import Bandpass
        from wwt_data_formats.folder import Folder
        from wwt_data_formats.place import Place

        def walk(f):
            for c in f.children:
                if isinstance(c, Folder):
                    yield from walk(c)
                elif isinstance(c, Place):
                    yield c

        for path in a.apply:
            f = Folder.from_file(path)
            n = 0
            for p in walk(f):
                for im in (p.foreground_image_set, p.image_set, p.background_image_set):
                    if im is None:
                        continue
                    m = re.search(r"/images/([^/]+)/?$", im.credits_url or "")
                    info = load_avm(feed, m.group(1)) if m else None
                    if info is None:
                        print(f"WARN {path}: no AVM for {im.credits_url}", file=sys.stderr)
                        continue
                    r = assign(m.group(1), info)
                    im.band_pass = Bandpass(r["bandpass"])
                    for attr, value in (("bands", r["bands"]), ("dominant_band", r["dominant"])):
                        if value:
                            setattr(im.xmeta, attr, value)
                        elif hasattr(im.xmeta, attr):
                            delattr(im.xmeta, attr)
                    n += 1
            with open(path, "wb") as fh:
                f.write_xml(fh, dest_wants_bytes=True)
            print(f"{path}: {n} imagesets banded")
        return

    ids = a.ids
    if not ids:
        found = set()
        for sub in ("cache_done", "cache_todo", "cache_failed", "_hold_large"):
            p = os.path.join(feed, sub)
            if os.path.isdir(p):
                found.update(os.listdir(p))
        p = os.path.join(feed, "_triage")
        if os.path.isdir(p):
            found.update(x[:-5] for x in os.listdir(p) if x.endswith(".json"))
        ids = sorted(found)
    rows = []
    for uid in ids:
        info = load_avm(feed, uid)
        if info is None:
            print(f"WARN no AVM for {uid}", file=sys.stderr)
            continue
        rows.append(assign(uid, info))
    for r in rows:
        line = f"{r['id']}\t{r['bandpass']}\t{r['bands']}\t{r['dominant']}\t{r['why']}\t{r['title']}"
        if r["flag"]:
            line += "\t" + r["flag"]
        sys.stdout.buffer.write((line + "\n").encode("utf-8"))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
