
### HiPS (asked: can WWT use a Euclid all-sky HiPS as a background?)
No all-sky Euclid HiPS exists. CDS (not ESA) publishes Euclid HiPS: `CDS/P/Euclid/ERO/color` (+ VIS,
NISP Y/J/H; ~0.027% of the sky), `CDS/P/Euclid/ERO/FirstImages`, `CDS/P/Euclid/Q1/color` (+ per band;
0.163% ≈ 67 deg², CC BY-NC 3.0 IGO), `CDS/P/Euclid/Q1/color-azulero` (2026-08-31),
`CDS/P/Euclid/NGC6505-Einstein-Ring`. ESA's Q1/Q2 pages say ESASky carries Euclid HiPS too (not
checkable today: ESASky was down). No DR1 HiPS in the IVOA HiPS registry yet (DR1-Foundation, 12 Nov
2026, covers ~1,900 deg² ≈ 4.6%; full DR1 mid-2027). WWT can draw these as Projection="Healpix"
imagesets (`.../Norder{0}/Dir{1}/Npix{2}`), but WWT's live `catalog.aspx?W=hips` snapshot (1,071 CDS
HiPS) has no Euclid entry. They'd need adding by hand, as foreground/overlay surveys, not backgrounds.
 back as
  candidates; they are parked in `_in_db/`. M78 was retiled here only as a placement control: its
  `processed/` output is NOT in the deliverable (don't upload it).
- New with WCS, tiled (17 minus M78 control = 16):
  - May 2024 ERO: 20240523a (Abell 2764), b (Dorado group), d (Abell 2390), e (NGC 6744).
  - Oct 2024 southern-sky mosaic: 20241015a (full 132 deg² mosaic at 10"/px) and its five zoom crops b–f.
  - Mar 2025 Q1: 20250319f (EDFS), g (EDFN), k (EDFF), l (Cat's Eye, 0.1"/px zoom of EDFN).
  - 20251002a (NGC 6505 Einstein ring, released 2025-02-10), 20251105a (dark cloud LDN 1641).
- Duplicates (`_dupes/`): 20250319h (= l, as JPEG), i (EDFN at half size), j (= g, as JPEG), m (= k, as JPEG).
- No WCS (`rejects/`): spacecraft artwork (20230612a, 20230901a); Q1 sky map, lens and morphology
  collages, 70x/16x zoom frames (20250319a–e); Q2 galactic bulge survey (20260624a: VIS + CFHT MegaCam
  colour, 27k x 22.5k; 20260624b sky map); DR1-Foundation 2026-11-12 (20261112a, c–i; b not on
  AstroPix). The originals' embedded XMP has AVM without any Spatial.* fields, so these need plate
  solving (or registration like EDFS below) before they can be used.

### WCS fixes (candidate JSON patched; originals in `_orig_candidates/`)
- 20250319f EDFS: AstroPix WCS was wrong (RA 50.03, Dec +52.19, rot 0). The Q1 mosaics are
  galactic-aligned (EDFN/EDFF AVM rotation = -(PA of galactic north) to 0.02°), so rotation = -101.85°;
  centre registered to DSS2 Red: RA 61.231592, Dec -48.42903. Residual < 1" overall, <= 3.6" in edge blocks.
- 20250319l Cat's Eye: ReferenceDimension published as 15136², image is 15136x15224 (stretched Dec 0.6%).

The patched JSONs live only in the git-ignored `candidates/`; a later `refresh` rewrites them from
AstroPix, so re-apply both patches before ever re-tiling 20250319f or l.

### Astrometric corrections (`astrometry.json`, applied by `build_euclid.py`)
ENSCI's AVM sits 2–4" north-west of DSS2 Red, and the database's own placements of the six existing
images differ from their AVM the same way. Each image was shifted by its own DSS2-measured offset
(or registered to an overlapping corrected Euclid image when its field is too small for DSS2).
The Q1 mosaics also had pixel-scale errors (EDFN +0.0975%: 11" at the corners; EDFF -0.044%, EDFS
-0.032%) and tiny rotations, fitted on a 3x3 grid of crops; after correction they match DSS2 to
0.8" / 0.2" / 1.2" rms. LDN 1641 is low confidence (dark cloud, few stars). The 32° Oct 2024 mosaic
(10"/px) is left as published.
Checkers: `check_hips.py`, `fit_field.py`, `corr_hdr.py` (session scratchpad; copies are in the shared
side-session notes folder): SkyView DSS2 + reproject + phase correlation. CDS alasky/hips2fits and
ESASky were down on 2026-11-14, and SkyView's 2MASS/WISE paths returned errors.

### Build
`cd feeds/euclid && python build_euclid.py --out euclid.wtml <ids>` writes
`processed/<id>/index.wtml` (BandPass="IR" + Xbands="Visible,IR" + Xdominant_band="IR", like `cattool
emit`) and `euclid.wtml` (BandPass="Multi"; the ingest input: new Places only, newest first).

### Ingest (NOT done) — the existing six must not go through ingest
`cattool ingest` reuses an imageset by URL but always mints a new Place, so `euclid.wtml` holds only the
new images and `catfiles/euclid.yml` already lists the six existing Place UUIDs. From the repo root:

    $WWTPY cattool.py ingest feeds/euclid/euclid.wtml --cx-handle=skip --prepend-to=catfiles/euclid.yml
    $WWTPY cattool.py emit

Dry run on 2026-11-14 in a throwaway copy of this branch: additions only (16 imagesets in
`imagesets/sky__multi.xml` with BandPass="Multi", Xbands, Xdominant_band, Xcxstatus="skip",
Xcorepipe_ids, Xastropix_ids; 16 Places across 8 `places/sky_ra*.yml`); `catfiles/euclid.yml` gets the
16 new Places above the existing six; emitted `euclid.wtml` = 22 Places, all written BandPass="IR";
no `&amp;amp;`. Nothing else in the DB changed.

### Upload (user)
`feeds/euclid/processed/ensci_<id>/` -> `data1.wwtassets.org/feeds/euclid/ensci_<id>/` for the 16 ids in
`euclid.wtml` (NOT ensci_euclid20240523c), 3.7 GB in total. Then `check_blobs.py feeds/euclid/euclid.wtml`.
The working files (cache_done originals, processed tiles) are git-ignored and live in this worktree:
move `feeds/euclid/` contents to the main checkout before removing the worktree.

### Decided (user, 2026-11-14)
- Keep the Oct 2024 zoom crops (20241015b–f) and the Cat's Eye. Rubin's "full field of view only" rule
  doesn't apply to Euclid: its full fields are downsampled previews (EDFN 1.2"/px vs Cat's Eye 0.1"/px;
  mosaic 10"/px vs crops down to 0.05"/px), so the crops carry detail nothing else has.

### Open decisions for the user
- Folder thumbnail is the existing Horsehead thumb.jpg. ESA's spacecraft photos are "ESA Standard
  Licence" (not CC); AstroPix only has artwork.
- No Explore-root entry yet (exploreroot6.yml / explorerootweb.yml).
