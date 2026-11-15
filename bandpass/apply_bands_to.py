"""Set BandPass on newly ingested imagesets with the propose_bandpass.py rules.

    python bandpass/apply_bands_to.py BATCH.wtml [--dry-run]

Runs `propose_bandpass.decide()` for every imageset whose URL appears in
BATCH.wtml (normally the ingest WTML of a feed batch) and applies the result:
a single band, or BandPass="Multi" with Xbands and Xdominant_band. Rows that
the rules mark "review" are left as ingested and listed. The database is
rewritten with cattool's `ImagesetDatabase.rewrite()`.
"""

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bandpass"))

import cattool  # noqa: E402
import propose_bandpass as pb  # noqa: E402
from wwt_data_formats.enums import Bandpass  # noqa: E402


def main():
    batch = Path(sys.argv[1]).read_text(encoding="utf-8")
    dry = "--dry-run" in sys.argv
    urls = set(re.findall(r'Url="([^"]+\{1\}[^"]*)"', batch))
    descs, colls = pb.load_places_and_collections()
    wanted = [s for s in pb.load_imagesets() if s["url"] in urls]
    idb = cattool.ImagesetDatabase()
    tally, review = Counter(), []
    for s in wanted:
        d = pb.decide(s, descs.get(s["url"], []), colls.get(s["url"], set()))
        if d["confidence"] == "review":
            review.append((s["name"], d["evidence"]))
            continue
        img = idb.by_url[s["url"]]
        img.band_pass = Bandpass(d["proposed"])
        if d["proposed"] == "Multi":
            img.xmeta.bands = d["components"].replace("+", ",")
            img.xmeta.dominant_band = d["dominant"]
            tally["Multi " + d["components"]] += 1
        else:
            tally[d["proposed"]] += 1
    print(f"{len(wanted)} of {len(urls)} batch imagesets found in the database")
    for k, n in tally.most_common():
        print(f"{n:5d}  {k}")
    for name, why in review:
        print(f"review: {name}: {why}")
    if not dry:
        idb.rewrite()
        print("imagesets/ rewritten")


if __name__ == "__main__":
    main()
