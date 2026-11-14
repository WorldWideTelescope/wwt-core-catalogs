"""Apply bandpass_proposal.csv to the imageset database.

    python bandpass/apply_bandpass.py [--dry-run]

For each row: `your_bandpass` if filled in, else `proposed`, except rows
marked `review` (left as they are unless `your_bandpass` is set). Multi-band
images get BandPass="Multi" plus Xbands="XRay,Visible,..." (their component
bands, short to long wavelength). The database is rewritten with cattool's
own `ImagesetDatabase.rewrite()`, which regroups imagesets into
`imagesets/<type>_<bandpass>.xml` files.

Needs a wwt_data_formats with Bandpass.MULTI (the user's fork, branch
`multi-bandpass`).
"""

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cattool  # noqa: E402
from wwt_data_formats.enums import Bandpass  # noqa: E402

CSV = Path(__file__).resolve().parent / "bandpass_proposal.csv"


def main():
    dry = "--dry-run" in sys.argv
    if not hasattr(Bandpass, "MULTI"):
        sys.exit("wwt_data_formats lacks Bandpass.MULTI: install the multi-bandpass fork first")

    idb = cattool.ImagesetDatabase()
    changed, missing = Counter(), []
    for row in csv.DictReader(CSV.open(encoding="utf-8-sig")):
        choice = row["your_bandpass"].strip()
        if not choice:
            if row["confidence"] == "review":
                continue
            choice = row["proposed"]
        img = idb.by_url.get(row["url"])
        if img is None:
            missing.append(row["url"])
            continue
        new = Bandpass(choice)
        comps = row["components"] if new == Bandpass.MULTI else ""
        old_comps = getattr(img.xmeta, "bands", "")
        if img.band_pass == new and old_comps == comps.replace("+", ","):
            continue
        changed[(img.band_pass.value, new.value)] += 1
        img.band_pass = new
        if comps:
            img.xmeta.bands = comps.replace("+", ",")
        elif hasattr(img.xmeta, "bands"):
            delattr(img.xmeta, "bands")

    for (a, b), n in sorted(changed.items(), key=lambda kv: -kv[1]):
        print(f"{n:5d}  {a} -> {b}")
    print(f"{sum(changed.values())} imagesets changed; {len(missing)} CSV rows not in the database")
    if not dry:
        idb.rewrite()
        print("imagesets/ rewritten")


if __name__ == "__main__":
    main()
