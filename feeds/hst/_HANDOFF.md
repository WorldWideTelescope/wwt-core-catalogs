# HST feed (ESA/Hubble, esahubble.org) — handoff

## 2026-11-14: catch-up batch (347 images, 2019-07 → 2026-11)

State: tiled, **ingested** into `catfiles/studieshubble.yml` ("Hubble Studies"; emitted
`studieshubble.wtml` = 1,696 places, 347 new at the top, newest first). **Tiles not yet
uploaded** (the user uploads them by hand).

### What was there
The catalogue's ESA/Hubble entries stopped in mid-2019 (potw1926a), plus three one-offs
(heic2007a, heic2011b, heic2102a) and the M31 PHAST package (heic2501a). `refresh` lists 3,013
Observation images on esahubble.org: 1,019 already tagged `hst|…`, 1,994 candidates, of which
`find_new.py` reports 1,932 not in the DB. Only **434** are releases after the catalogue's
newest (ids `*19xx`–`*26xx`); the ~1,500 older ones were never imported and are out of scope.

### Selection (per-image record: `hst_2026-11_decisions.tsv`)
AVM for the 434 was cached in `_triage/` before anything was downloaded; WCS, pixel scale
and footprints come from it.

| result | n | why |
|---|---|---|
| tiled + ingested | 347 | |
| skipped: not Hubble data | 33 | 19 DSS2 wide-field context frames, 10 Webb-only mirrors (heic2414b, heic2614c-f, sci23002a/3a, sci25006a, sci26004b, sci26006a), Euclid potm2602c, Gemini ann2104c, amateur heic2106b, DSS heic2021c |
| skipped: duplicate of a DB image | 22 | same picture already catalogued; kept the sharper/larger (see below) |
| skipped: crop of a larger image in this batch | 19 | same pixel scale, footprint inside the bigger one |
| skipped: same field in this batch | 3 | heic2020b (1996 epoch, kept 2016 heic2020c), potw2039a (kept larger potw2450a), potw2445c (no-SN copy of potw2445a) |
| skipped: no WCS | 7 | |
| skipped: title | 2 | heic2313b "wide-field view" (ground-based), potw2413a "No zoom" |
| failed | 1 | potw2240a: AVM WCS tagged for 3430x2240, the original is 3430x2735 |

Duplicate rule (user): pixel density — drop the smaller crop unless it is sharper. Footprints
are compared with each image's own AVM WCS (DB entries from esahubble/esawebb/eso had their AVM
fetched into `_dbavm/`; hubblesite ones use the tile pyramid, marked `~`).
- Same image already in the DB via the JWST feed (same title): heic2310a = weic2327a,
  heic2414a = weic2426a, heic2614b = weic2622b, sci25004a = potm2503a.
- Same Hubble data republished on esawebb resampled to the NIRCam grid (0.031"/px), which wins
  on pixel density: heic2211a, heic2502a (NGC 346, vs weic2301c); and, by the user's decision
  of 2026-11-14 (same title, same data and credits, checked in the AVM), potw2448a (kept
  esawebb potm2411b) and potw2329a (kept esawebb potm2608b). These two were tiled and ingested
  first, then removed from the DB; their tiles are in `on-hold/` (not for upload).
- Smaller re-crops / re-processings of older ESA/Hubble images at the same scale:
  potw2305a/2503a/2506a/2519a/2531a (Tarantula, inside heic1206a), heic2607b (Crab from
  1999/2000 data, = heic0515a), potw1933a, potw2534a, potw2547a, potw2550a, potw2552a,
  potw2524a, potw2118a (eso1514a), potw2248a (hubblesite 2003, approx).
- **New epochs kept by user decision (2026-11-14)** although the rule would drop them (same
  field and density as an older image): heic2607a (Crab, 2024 data), heic2203a (Earendel, 2022)
  and heic2407a (UGC 12158, 2024).
- Kept both (smaller one is sharper): ~85 pairs.

### Superseded older entries — FLAGGED, not removed (`superseded_2026-11.tsv`)
45 catalogued imagesets (old id, name, imageset URL, credits URL) that 26 of the new images
supersede: either the old image lies inside the new one and is not sharper, or (for the three
new epochs) it shows the same field at the same density. Per the user (2026-11-14) they stay
in the catalogue unchanged; the list is for a later pruning decision. E.g. heic2604a (Egg)
over opo9711b and potw1217a; potw2542b over the six tiny opo0324e-j crops; heic2607a over six
older Crab images.

### Bands (`../../bandpass/band_for_avm.py`)
From the AVM exposure list, with propose_bandpass.py's telescope table: Hubble exposures are
UV below 380 nm, IR at 950 nm and up (WFC3/IR, NICMOS), else Visible; a Hubble image is IR
or Ultraviolet only when every exposure is; a fixed-band partner (Webb, Chandra, VLA …) makes
it `Multi` with `Xbands` and `Xdominant_band` = the partner's band; ground-based optical
partners (DECam, SDSS, VLT …) don't. A band named in the title wins when the AVM has it.
Result: 324 Visible, 20 IR, 1 Ultraviolet (heic1912a "Cosmic Fireworks in Ultraviolet"),
2 Multi (heic2609b Visible,IR→IR; opo1944a XRay,Visible,Radio→XRay).
Every `index.wtml` carries the band (verified: 0 mismatches).

### Files
- Tiles: `processed/<id>/` (347 dirs, ~11 GB) with `index.wtml` (https, `Xcorepipe_ids="hst|<id>"`)
  → upload each to blob `feeds/hst/<id>/` on data1.wwtassets.org. **The worktree
  hst-feed-update-1927c7 holds the only copy; don't remove it before the upload.** Source
  TIFFs were deleted after tiling.
- Merged, newest first: `_merge/hst-new-2026-11-merged.wtml` (347 places, 0 artifacts);
  `_merge/hst-epochs-2026-11.wtml` (the 3 epochs, ingested separately).
- `check_collisions.py` vs DataStories JWST app: 0 DUP; the NAME clashes were resolved above.

### Ingest (done)
`cattool ingest feeds/hst/_merge/hst-new-2026-11-merged.wtml --cx-handle=hubble
--prepend-to=catfiles/studieshubble.yml` (existing HST imagesets are `queue:hubble`;
Constellations is discontinued, so no register-cxprep), then the two drops removed and the
three epochs ingested the same way, and the new block of `studieshubble.yml` re-sorted newest
first. Multi entries keep BandPass="Multi" in the DB; emit writes Xdominant_band.

### Next
1. User uploads the `processed/<id>/` dirs; then
   `check_blobs.py feeds/hst/_merge/hst-new-2026-11-merged.wtml`.
2. Upload emitted `studieshubble.wtml` to wwtfiles `catalog` (blob `studieshubble.wtml`),
   bump DataVersion in `wwt6_login.txt`.
3. Later: decide on pruning the entries in `superseded_2026-11.tsv`.
