"""Propose a BandPass for every sky imageset in the core catalogues.

Most sky imagesets say BandPass="Visible" whatever they show (every JWST,
Spitzer and Chandra image included). This reads the imageset database, the
places and the catfiles, gathers the evidence for each imageset (its feed or
publisher, the collection it sits in, the telescopes and bands named in its
credits and title, and as weaker evidence its description) and writes a CSV
to review:

    python bandpass/propose_bandpass.py            # -> bandpass/bandpass_proposal.csv

Nothing in the catalogue is changed. Columns:

    url, name                 the imageset (url is cattool's key)
    current                   BandPass in the database now
    proposed                  what the evidence says; "Multi" when it spans bands
    dominant                  a single valid BandPass for a multi-band image
                              (the headline band), for use if "Multi" is not added
    components                every band found, short to long wavelength
    change                    yes when proposed differs from current
    confidence                high: a single-band telescope or a band named in the
                              title/credits; medium: a multi-band telescope's
                              default band or a composite described in words;
                              low: little or no evidence; review: the catalogue
                              already has a non-visible band that the evidence
                              disagrees with (kept as is)
    telescope                 the primary telescope (feed, publisher, collection)
    telescopes_credited       telescopes named in the credits or title
    evidence                  why, in a few words
    collections               catfiles the imageset appears in
    credits, credits_url
    your_bandpass             blank: fill in to override

Bands use the wwt_data_formats spellings (XRay, IR, HydrogenAlpha ...).
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "bandpass_proposal.csv"

ORDER = ["Gamma", "XRay", "Ultraviolet", "Visible", "HydrogenAlpha", "IR", "Microwave", "Radio"]

# Telescopes: (label, bands, fixed). A fixed telescope observes in one band
# (or a fixed set), so naming it says which band the data are. A variable one
# (Hubble, VLT, Gemini ...) has instruments in several bands: it contributes
# its default band only when nothing names a band explicitly.
TELESCOPES = [
    ("JWST", {"IR"}, True, r"\bjwst\b|\bwebb\b|nircam|\bmiri\b|niriss|nirspec|\bcsa\b"),
    ("Euclid", {"Visible", "IR"}, True, r"\beuclid\b"),
    ("Chandra", {"XRay"}, True, r"chandra|\bcxc\b"),
    ("XMM-Newton", {"XRay"}, True, r"\bxmm\b|xmm-newton"),
    ("ROSAT", {"XRay"}, True, r"\brosat\b"),
    ("NuSTAR", {"XRay"}, True, r"nustar"),
    ("eROSITA", {"XRay"}, True, r"erosita"),
    ("Suzaku", {"XRay"}, True, r"suzaku"),
    ("Fermi", {"Gamma"}, True, r"\bfermi\b"),
    ("CGRO", {"Gamma"}, True, r"\begret\b|comptel|\bcgro\b|compton gamma"),
    ("GALEX", {"Ultraviolet"}, True, r"galex"),
    ("Spitzer", {"IR"}, True, r"spitzer|\birac\b|\bmips\b|\bssc\b"),
    ("WISE", {"IR"}, True, r"(?<!astro-)\bwise\b|neowise"),
    # Not William/John/Caroline Herschel, nor the William Herschel Telescope.
    ("Herschel", {"IR"}, True,
     r"esa/herschel|herschel/(pacs|spire)|herschel space|(?<!william )herschel (observatory|telescope|data|image)|\bpacs\b|\bspire\b"),
    ("SOFIA", {"IR"}, True, r"\bsofia\b"),
    ("IRAS", {"IR"}, True, r"\biras\b"),
    ("2MASS", {"IR"}, True, r"2mass"),
    ("AKARI", {"IR"}, True, r"akari"),
    ("VISTA", {"IR"}, True, r"\bvista\b|vircam"),
    ("UKIRT", {"IR"}, True, r"ukirt"),
    ("Planck", {"Microwave"}, True, r"(?<!max-)(?<!max )\bplanck\b(?!-institut| institut)"),
    ("WMAP", {"Microwave"}, True, r"\bwmap\b"),
    ("ALMA", {"Radio"}, True, r"\balma\b"),
    ("APEX", {"Radio"}, True, r"\bapex\b"),
    ("JCMT", {"Radio"}, True, r"\bjcmt\b|scuba"),
    ("VLA", {"Radio"}, True, r"\bvla\b|\bjvla\b|very large array"),
    ("VLBA", {"Radio"}, True, r"\bvlba\b"),
    ("GBT", {"Radio"}, True, r"\bgbt\b|green bank"),
    # NRAO as a data credit ("NRAO/AUI/NSF"), not an author's affiliation.
    ("NRAO", {"Radio"}, True, r"nrao/aui|aui/nrao|nrao/vla|vla/nrao|nrao/gbt|gbt/nrao|^\s*nrao\b"),
    ("LOFAR", {"Radio"}, True, r"lofar"),
    ("MeerKAT", {"Radio"}, True, r"meerkat"),
    ("ASKAP", {"Radio"}, True, r"askap"),
    ("ATCA", {"Radio"}, True, r"\batca\b|australia telescope compact"),
    ("Parkes", {"Radio"}, True, r"\bparkes\b"),
    ("Effelsberg", {"Radio"}, True, r"effelsberg"),
    ("MWA", {"Radio"}, True, r"\bmwa\b|murchison widefield"),
    ("Hubble", {"Visible"}, False, r"hubble|\bhst\b|wfpc2|\bacs\b|wfc3"),
    ("VLT", {"Visible"}, False, r"\bvlt\b|very large telescope|\bfors\d?\b|\bmuse\b"),
    ("VST", {"Visible"}, False, r"\bvst\b|omegacam"),
    ("MPG/ESO 2.2m", {"Visible"}, False, r"mpg/eso|\bwfi\b|2\.2-metre|2\.2m"),
    ("Gemini", {"Visible"}, False, r"gemini"),
    ("Subaru", {"Visible"}, False, r"subaru|hyper suprime|\bhsc\b"),
    ("CFHT", {"Visible"}, False, r"\bcfht\b|canada-france-hawaii"),
    ("Keck", {"Visible"}, False, r"\bkeck\b"),
    ("Rubin", {"Visible"}, False, r"\brubin\b|\blsst\b"),
    ("DECam", {"Visible"}, False, r"decam|dark energy camera|blanco"),
    ("KPNO", {"Visible"}, False, r"\bkpno\b|kitt peak|mayall|\bwiyn\b"),
    ("CTIO", {"Visible"}, False, r"\bctio\b|cerro tololo|\bsoar\b"),
    ("SDSS", {"Visible"}, False, r"\bsdss\b|sloan digital"),
    ("DSS", {"Visible"}, False, r"\bdss\d?\b|digitized sky survey"),
]
TEL_RE = [(lab, bands, fixed, re.compile(pat, re.I)) for lab, bands, fixed, pat in TELESCOPES]
TEL_BY_LABEL = {lab: (bands, fixed) for lab, bands, fixed, _ in TELESCOPES}

# Instruments that pin a variable telescope to the infrared.
IR_INSTRUMENTS = re.compile(
    r"nicmos|wfc3[/ -]?ir|hawk-?i|\bnaco\b|visir|sphere|\bkmos\b|isaac|sinfoni|\bsofi\b|eris"
    r"|\bniri\b|gnirs|\bnifs\b|gsaoi|flamingos|\bnici\b|wircam|nirc2|\bmoircs\b", re.I)

# Bands named in words. "Optical:" etc. in credits (Chandra's style) count.
BAND_WORDS = [
    # Object types ("gamma-ray burst", "X-ray binary", "radio galaxy",
    # "luminous infrared galaxy") say nothing about the image's band.
    ("Gamma", re.compile(r"gamma[- ]?rays?(?![- ]?burst)", re.I)),
    ("XRay", re.compile(r"x[- ]?rays?\b(?![- ]?(binar|pulsar|burst))", re.I)),
    ("Ultraviolet", re.compile(r"ultra-?violet|\buv\b", re.I)),
    ("HydrogenAlpha", re.compile(r"h[- ]?alpha|hα|hydrogen[- ]alpha", re.I)),
    ("IR", re.compile(r"infra-?red(?![- ](luminous|galax|bright))|\b(near|mid|far)[- ]ir\b|\bir\b", re.I)),
    ("Microwave", re.compile(r"microwave", re.I)),
    ("Radio", re.compile(
        r"\bradio\b(?![- ](galax|source|loud|quiet|jet|lobe|pulsar))|sub-?millimet(er|re)|millimet(er|re)[- ](wave|wavelength)", re.I)),
    ("Visible", re.compile(r"\boptical\b|visible[- ]light|\bvisible\b", re.I)),
]
# In a description, a band counts only as data: "infrared light", "X-ray
# data", "radio observations" -- not "X-ray emission" or "infrared-bright".
DATA_NOUN = r"(?:[- ](?:light|data|observations?|images?|views?|wavelengths?|camera|telescope|observatory))"
DESC_BAND_WORDS = [(b, re.compile("(?:" + rx.pattern + ")" + DATA_NOUN, re.I)) for b, rx in BAND_WORDS]

# Catalogue designations and field names that mention a telescope without
# being its data: IRAS 16423+2353, 2MASX J2057..., SDSS J1652..., WISE J...,
# the Hubble (Ultra) Deep Field, Hubble's law.
NOT_A_TELESCOPE = re.compile(
    r"\b(?:iras|2mas[sx]|sdss|wise|galex|xmm|rosat|1rxs|rx|nvss|first)\s?j?\s?[+-]?\d[\d.+-]*"
    r"|hubble (?:ultra[- ])?deep field|hubble'?s? (?:law|constant|tension|variable nebula|classification|sequence)",
    re.I)

COMPOSITE = re.compile(
    r"composite|multi-?wavelength|combin(es|ed|ing|ation of) (the )?(data|observations|images|views)"
    r"|data from (several|multiple|different|\w+ different) (telescopes|observatories)", re.I)

# Primary telescope from the publisher/pipeline id, feed path, collection or host.
PUBLISHER = {
    "esahubble": "Hubble", "stsci": "Hubble", "hst": "Hubble", "jwst": "JWST", "chandra": "Chandra",
    "spitzer": "Spitzer", "wise": "WISE", "nrao": "NRAO", "planck": "Planck", "rubin": "Rubin",
    "eso": "ESO", "noirlab": "NOIRLab",
}
COLLECTION = {
    "jwst": "JWST", "studieschandra": "Chandra", "studiesspitzer": "Spitzer", "wise": "WISE",
    "studieshubble": "Hubble", "collection_sofia": "SOFIA", "geministudies": "Gemini", "rubin": "Rubin",
    "studiesnoao": "NOIRLab", "eso": "ESO",
}
# Observatory labels that aren't one telescope: their default band only.
TEL_BY_LABEL.update({"ESO": ({"Visible"}, False), "NOIRLab": ({"Visible"}, False)})


def sort_bands(bands):
    return sorted(bands, key=lambda b: ORDER.index(b) if b in ORDER else 99)


def text(el, tag):
    t = el.find(tag)
    return (t.text or "").strip() if t is not None else ""


def load_imagesets():
    out = []
    for f in sorted((ROOT / "imagesets").glob("sky_*.xml")):
        for el in ET.parse(f).getroot().iter("ImageSet"):
            if el.get("DataSetType") != "Sky":
                continue
            out.append({
                "url": el.get("Url", ""),
                "name": el.get("Name", ""),
                "current": el.get("BandPass", "Visible"),
                "projection": el.get("Projection", ""),
                "astropix": el.get("Xastropix_ids", ""),
                "corepipe": el.get("Xcorepipe_ids", ""),
                "credits": text(el, "Credits"),
                "credits_url": text(el, "CreditsUrl"),
                "description": text(el, "Description"),
            })
    return out


def load_places_and_collections():
    """url -> place descriptions, and url -> catfile names."""
    by_uuid, desc = {}, defaultdict(list)
    for f in sorted((ROOT / "places").glob("*.yml")):
        for doc in yaml.safe_load_all(f.read_text(encoding="utf-8")):
            if not doc:
                continue
            url = doc.get("foreground_image_set_url") or doc.get("background_image_set_url")
            if url:
                by_uuid[doc["_uuid"]] = url
                if doc.get("description"):
                    desc[url].append(str(doc["description"]))
    colls = defaultdict(set)
    for f in sorted((ROOT / "catfiles").glob("*.yml")):
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"-\s+'?(place|imageset)\s+(\S+?)'?\s*$", line)
            if not m:
                continue
            url = by_uuid.get(m.group(2)) if m.group(1) == "place" else m.group(2)
            if url:
                colls[url].add(f.stem)
    return desc, colls


def primary_telescope(s, collections):
    for ids in (s["corepipe"], s["astropix"]):
        for one in filter(None, ids.split(",")):
            pub, _, item = one.partition("|")
            if pub == "ensci" and "euclid" in item.lower():
                return "Euclid", f"publisher id {one}"
            if pub in PUBLISHER:
                return PUBLISHER[pub], f"publisher id {pub}"
    u = s["url"].lower()
    m = re.search(r"/feeds/([a-z]+)/", u)
    if m and m.group(1) in PUBLISHER:
        return PUBLISHER[m.group(1)], f"feed {m.group(1)}"
    if "_euclid/" in u:
        return "Euclid", "package path"
    for c in sorted(collections):
        if c in COLLECTION:
            return COLLECTION[c], f"collection {c}"
    if "gemini.edu" in u:
        return "Gemini", "host gemini.edu"
    if "wmap" in u:
        return "WMAP", "tile URL"
    if "planck" in u:
        return "Planck", "tile URL"
    return "", ""


def split_credits(credits):
    """Credits often carry the description after a ';'. Keep the credit-like
    parts (short, or "X-ray: ..." labels); return the prose separately."""
    keep, prose = [], []
    for part in credits.split(";"):
        p = part.strip()
        # Once the description starts, the rest is description too.
        if not prose and (len(p) <= 140 or re.match(r"(x-ray|optical|radio|infrared|ir|uv|ultraviolet|visible|gamma|h-alpha)\s*:", p, re.I)):
            keep.append(p)
        else:
            prose.append(p)
    return "; ".join(keep), " ".join(prose)


# Survey names end in a band: "EGRET Hard (Gamma)", "RASS ... (X-ray)".
SURVEY_SUFFIX = {
    "gamma": "Gamma", "x-ray": "XRay", "xray": "XRay", "uv": "Ultraviolet", "ultraviolet": "Ultraviolet",
    "optical": "Visible", "visible": "Visible", "h-alpha": "HydrogenAlpha", "halpha": "HydrogenAlpha",
    "ir": "IR", "infrared": "IR", "microwave": "Microwave", "radio": "Radio",
}


def decide(s, descs, collections):
    credits, credit_prose = split_credits(s["credits"])
    strong = NOT_A_TELESCOPE.sub(" ", " ".join([s["name"], credits]))
    m = re.search(r"\(([a-z-]+)\)\s*$", s["name"], re.I)
    suffix_band = SURVEY_SUFFIX.get(m.group(1).lower()) if m else None
    primary, primary_why = primary_telescope(s, collections)

    credited = []
    for lab, _, _, rx in TEL_RE:
        if rx.search(strong) or rx.search(s["credits_url"]):
            credited.append(lab)
    explicit = {b for b, rx in BAND_WORDS if rx.search(strong)}
    if IR_INSTRUMENTS.search(strong):
        explicit.add("IR")
    if suffix_band:
        # A survey's own label is the answer; other bands named in its credits
        # are processing notes, not data.
        explicit = {suffix_band}
        credited = [t for t in credited if suffix_band in TEL_BY_LABEL[t][0]]

    bands, why = set(explicit), []
    if explicit:
        why.append("named: " + "+".join(sort_bands(explicit)))
    for lab in credited:
        tb, fixed = TEL_BY_LABEL[lab]
        if fixed or not explicit:
            bands |= tb
    fixed_credited = [t for t in credited if TEL_BY_LABEL[t][1]]
    if fixed_credited:
        why.append("credits: " + ", ".join(fixed_credited))
    elif credited and not explicit:
        why.append("credits: " + ", ".join(credited) + " (default band)")

    confidence = "high" if (explicit or fixed_credited) else "medium" if credited else ""
    if not bands and primary:
        tb, fixed = TEL_BY_LABEL.get(primary, ({"Visible"}, False))
        bands |= tb
        why.append(f"{primary_why} -> {primary}")
        confidence = "high" if fixed else "medium"

    # Descriptions: weaker. A composite described in words can widen a band set,
    # and a lone telescope or band mention can fill an empty one.
    desc = NOT_A_TELESCOPE.sub(" ", " ".join([s["description"], credit_prose, *descs]))
    if desc.strip():
        dbands = {b for b, rx in DESC_BAND_WORDS if rx.search(desc)}
        dtels = [lab for lab, _, fixed, rx in TEL_RE if fixed and rx.search(desc)]
        for lab in dtels:
            dbands |= TEL_BY_LABEL[lab][0]
        if COMPOSITE.search(desc) and len(dbands | bands) > len(bands) and len(dbands) >= 2:
            added = dbands - bands
            bands |= dbands
            why.append("description (composite): +" + "+".join(sort_bands(added)))
            confidence = "medium"
        elif not bands and len(dbands) == 1:
            bands |= dbands
            why.append("description mentions " + next(iter(dbands)))
            confidence = "low"

    if not bands:
        bands = {"Visible"}
        why.append("no evidence; Visible assumed")
        confidence = "low"

    comps = sort_bands(bands)
    proposed = comps[0] if len(comps) == 1 else "Multi"
    current = s["current"]
    if current not in ("Visible", "VisibleNight"):
        # The catalogue already says something specific: keep it unless the
        # evidence only widens it to Multi, and flag disagreements for review.
        if proposed == current:
            confidence = "high"
        elif proposed == "Multi" and current in comps:
            why.append(f"catalogue says {current}")
        else:
            why.append(f"evidence suggests {'+'.join(comps)}; kept catalogue value {current}")
            proposed, comps, confidence = current, [current], "review"

    # The headline band of a multi-band image: the primary telescope's own band
    # if it's a single-band telescope, else the first non-visible band.
    dominant = comps[0]
    if len(comps) > 1:
        pb = TEL_BY_LABEL.get(primary, (set(), False))
        if pb[1] and len(pb[0]) == 1 and next(iter(pb[0])) in comps:
            dominant = next(iter(pb[0]))
        else:
            dominant = next((b for b in comps if b != "Visible"), comps[0])

    return {
        "proposed": proposed, "dominant": dominant, "components": "+".join(comps),
        "confidence": confidence, "telescope": primary, "telescopes_credited": ", ".join(credited),
        "evidence": "; ".join(why),
    }


def main():
    imagesets = load_imagesets()
    descs, colls = load_places_and_collections()
    rows = []
    for s in imagesets:
        d = decide(s, descs.get(s["url"], []), colls.get(s["url"], set()))
        rows.append({
            "url": s["url"], "name": s["name"], "current": s["current"], **d,
            "change": "yes" if d["proposed"] != s["current"] else "",
            "collections": ", ".join(sorted(colls.get(s["url"], ()))),
            "credits": s["credits"][:300], "credits_url": s["credits_url"], "your_bandpass": "",
        })
    rows.sort(key=lambda r: (r["change"] != "yes", r["telescope"], r["name"].lower()))
    cols = ["url", "name", "current", "proposed", "dominant", "components", "change", "confidence",
            "telescope", "telescopes_credited", "evidence", "collections", "credits", "credits_url", "your_bandpass"]
    with OUT.open("w", newline="", encoding="utf-8-sig") as fh:   # BOM so Excel reads UTF-8
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # Summary.
    print(f"{len(rows)} sky imagesets -> {OUT.relative_to(ROOT)}")
    print("\nproposed:", dict(Counter(r["proposed"] for r in rows).most_common()))
    print("changes:", sum(r["change"] == "yes" for r in rows), "| by confidence:",
          dict(Counter(r["confidence"] for r in rows if r["change"] == "yes").most_common()))
    print("\nchanges by primary telescope:")
    for (tel, prop), n in Counter((r["telescope"] or "(unknown)", r["proposed"]) for r in rows
                                  if r["change"] == "yes").most_common(30):
        print(f"  {n:5d}  {tel:12s} -> {prop}")
    print("\nmulti components:", dict(Counter(r["components"] for r in rows if r["proposed"] == "Multi").most_common(12)))
    print("\nprimary telescope:", dict(Counter(r["telescope"] or "(unknown)" for r in rows).most_common()))
    tel = Counter(t for r in rows for t in filter(None, r["telescopes_credited"].split(", ")))
    print("\ntelescopes credited (images naming each):", dict(tel.most_common()))


if __name__ == "__main__":
    sys.exit(main())
