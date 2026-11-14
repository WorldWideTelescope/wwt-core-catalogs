# HST feed (ESA/Hubble, esahubble.org) — handoff

## 2026-11-14: catch-up batch (346 images, 2019-07 → 2026-11)

State: tiled and upload-ready; **not uploaded, not ingested**.

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
| tiled | 346 | |
| skipped: not Hubble data | 33 | 19 DSS2 wide-field context frames, 10 Webb-only mirrors (heic2414b, heic2614c-f, sci23002a/3a, sci25006a, sci26004b, sci26006a), Euclid potm2602c, Gemini ann2104c, amateur heic2106b, DSS heic2021c |
| skipped: duplicate of a DB image | 23 | same picture already catalogued; kept the sharper/larger (see below) |
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
- Hubble data republished on esawebb resampled to the NIRCam grid (0.031"/px), which wins on
  pixel density: heic2211a, heic2502a (NGC 346, vs weic2301c).
- Smaller re-crops / re-processings of older ESA/Hubble images at the same scale:
  potw2305a/2503a/2506a/2519a/2531a (Tarantula, inside heic1206a), heic2607a+b (Crab, vs
  heic0515a), potw1933a, potw2534a, potw2547a, potw2550a, potw2552a, potw2524a, potw2118a
  (eso1514a), potw2248a (hubblesite 2003, approx), heic2203a (potw1743a), heic2407a (potw1035a).
  **Judgement calls for the user:** heic2607a (Crab, *2024* data), heic2203a (Earendel, 2022
  data) and heic2407a (2024 data) are new observations at the same density as the older
  image; the rule dropped them. Tile them if new epochs should be kept.
- Kept both (smaller one is sharper): ~85 pairs, e.g. potw2448a vs esawebb potm2411b, which
  share the title "Viewing a flaky disc" (also potw2329a/potm2608b) — rename if wanted.
- Newer, sharper/larger images that supersede DB entries (candidates for pruning from
  catfiles at ingest; `supersedes_db` column): 23 images, e.g. heic2604a (Egg) over opo9711b
  and potw1217a, potw2542b over the six tiny opo0324e-j crops.

### Bands (`../../bandpass/band_for_avm.py`)
From the AVM exposure list, with propose_bandpass.py's telescope table: Hubble exposures are
UV below 380 nm, IR at 950 nm and up (WFC3/IR, NICMOS), else Visible; a Hubble image is IR
or Ultraviolet only when every exposure is; a fixed-band partner (Webb, Chandra, VLA …) makes
it `Multi` with `Xbands` and `Xdominant_band` = the partner's band; ground-based optical
partners (DECam, SDSS, VLT …) don't. A band named in the title wins when the AVM has it.
Result: 323 Visible, 20 IR, 1 Ultraviolet (heic1912a "Cosmic Fireworks in Ultraviolet"),
2 Multi (heic2609b Visible,IR→IR; opo1944a XRay,Visible,Radio→XRay).
Every `index.wtml` carries the band (verified: 0 mismatches).

### Files
- Tiles: `processed/<id>/` (346 dirs, 11 GB) with `index.wtml` (https, `Xcorepipe_ids="hst|<id>"`)
  → upload each to blob `feeds/hst/<id>/` on data1.wwtassets.org. **This worktree holds the only
  copy; don't remove it before the upload.** Source TIFFs were deleted after tiling.
- Merged, newest first: `_merge/hst-new-2026-11-merged.wtml` (346 places, 0 artifacts).
- `check_collisions.py` vs DataStories JWST app: 0 DUP, 3 NAME (above), 45 NEAR.

### Next
1. User uploads `processed/<id>/` dirs; then `check_blobs.py _merge/hst-new-2026-11-merged.wtml`.
2. Ingest (main session): `cattool ingest feeds/hst/_merge/hst-new-2026-11-merged.wtml
   --cx-handle=hubble --prepend-to=catfiles/studieshubble.yml` (existing HST imagesets are
   `queue:hubble`; Constellations is discontinued, so no register-cxprep; prepend catfile
   `studieshubble`). Multi entries keep BandPass="Multi"; emit writes Xdominant_band.
3. Optionally prune the superseded DB places listed in the decisions TSV.
