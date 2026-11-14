# Chandra feed assessment (2026-11-14)

Research only; nothing has been tiled or ingested. Data: `chandra_assessment.csv`, one row per image (618 rows).

- **Set `a`**: the main image of each of the 233 Chandra photo-album releases from 2018 to 2026 (`chandra.harvard.edu/photo/YYYY/slug/`). Most releases also have extra panels in `more.html`. The CSV does not list these.
- **Set `b`**: the 385 Chandra imagesets already in the catalogue (`imagesets/sky__*.xml`), from 337 releases dated 1999–2017. Each is matched to the exact image in `more.html#imgN` when the credits URL names one.

## How the columns were filled

| Column(s) | Method |
| --- | --- |
| `avm_present`, `avm_level` | XMP read from range-fetched headers of the TIFF (first 1 MB, plus the last 2 MB when needed), the JPEG and the large JPEG. `full WCS` means `Spatial.ReferenceValue` plus `Scale` or `CDMatrix`. `position only` means only `ReferenceValue`. |
| `fits` | `openFITS` means the release has per-band FITS on Chandra's openFITS pages (`/photo/openFITS/`). No 2018+ release does. |
| `largest_px`, `largest_mpix`, `largest_bytes_MB` | Pixel size from the TIFF IFD or the JPEG SOF of the largest file offered: TIFF, Large JPEG or 4K JPEG. |
| `chandra_layer_tifs` | Separate per-band TIFFs Chandra offers, such as `_xray.tif` and `_optical.tif`. |
| `layers`, `nonchandra_layers` | Parsed from the release's "Credit" fact (the per-image credit for `more.html` images) and mapped to a facility. |
| `fullres_public` | Whether the facility publishes full-resolution data, from its archive type (press TIFF with AVM, MAST, IRSA, PS1 cutouts, …). |
| `fullres_match` | Verified matches. **(1)** ESA/Hubble, ESA/Webb, ESO and NOIRLab/Gemini searched by object name, then each candidate's `/api/json/` AVM checked to confirm it covers the Chandra field. **(2)** Imagesets of the same facility already in WWT that cover the field. A match counts only if it spans at least half the composite's field of view. |
| `layer_res_gain` | Composite pixel scale ÷ reference pixel scale (linear). The composite's scale comes from AVM, or else from the fact sheet "Scale" ÷ width. The fact-sheet scale can be badly off (see the M16 sample), so treat gains for rows without AVM as indicative. |
| `wwt_vs_current_res` (set b) | Pixel scale WWT tiled at ÷ pixel scale of the current Chandra TIFF. Above 1 means a sharper TIFF now exists. |
| `wwt_sep_arcmin` (set b) | Image identity check: distance between the image's AVM centre and the WWT centre. Above about 1′ usually means the entry maps to a different `more.html` panel. |
| `catalog_band_check` (set b) | Compares the catalogue's bands with the bands in the Chandra page credit. |
| `alignment_effort` | **easy**: AVM WCS or Chandra FITS is present. **medium**: a WCS-bearing reference for a layer exists, either a verified press AVM image, a WWT imageset, survey FITS, or (unverified) archive FITS for the credited facility; set-`b` rows can also reuse the existing WWT placement. **hard**: no reference layer, meaning X-ray-only images without AVM, or composites whose other layers are only radio, amateur or IXPE. |

## Counts

| | Set a (2018–2026) | Set b (catalogue) |
| --- | --- | --- |
| Images | 233 | 385 |
| AVM present: full WCS | **42** (18%) | **339** (88%) |
| AVM present: position only | 45 | 6 |
| AVM present: AVM block, no Spatial tags | 5 | 38 |
| AVM present: none | 141 | 2 |
| FITS available | 0 | 38 (openFITS) |
| TIFF offered | 228 | 385 |
| Median size of largest file | 13.0 Mpix | 8.9 Mpix |
| Largest files ≥ 20 Mpix | 64 (9 ≥ 50 Mpix) | 6 |
| Rows whose release offers per-band layer TIFFs | 194 | 342 |
| Single-band (X-ray only) | 66 | 177 |
| Composite | 167 | 208 |
| Composites with a verified full-res layer (press AVM or WWT imageset) | 61 | 114 |
| Layer resolution gain ≥ 2× | 18 | 23 |
| Layer resolution gain 1–2× | 13 | 25 |
| Effort: easy | 42 | 339 |
| Effort: medium | 123 | 46 (30 by reusing the WWT placement) |
| Effort: hard | 68 (58 X-ray-only, 10 composites) | 0 |

Facilities credited for non-Chandra layers:

- **Set a**: Hubble 72, Spitzer 26, JWST 22, NOIRLab 17, Pan-STARRS 16, XMM-Newton 14, SDSS 13, IXPE 11, VLA 11, DSS 10, ESO 9, MeerKAT 7, LOFAR 6, others ≤ 5.
- **Set b**: Hubble 95, Spitzer 53, DSS 35, VLA 35, NOIRLab 28, ESO 17, SDSS 13, ASKAP/ATCA 8, ROSAT 8, others ≤ 6.

Release counts per year are steady (22–30 in every year from 2018 to 2026). Full AVM tagging became the exception after 2017. Only 42 of the 2018+ images carry full AVM WCS: 11 in 2018, then 2–6 a year through 2026. Another 45 carry only a position. A position gives the field centre but not the scale or rotation. 85 of the 233 new releases revisit a field that already has a Chandra image in WWT (`existing_chandra_in_wwt`). The new image should replace the old one or be added beside it.

## Sample checks

**2018/m16** (Eagle Nebula, no AVM; composite of Chandra and Hubble). I downloaded `m16.tif` (2562², 16.6 MB) and the ESA/Hubble `heic1501a` large JPEG (6780×7071, carries AVM). `scripts/register_sample.py` registered them as follows:

- SIFT plus RANSAC similarity fit: 1,617 inliers out of 1,697 matches.
- Rotation relative to the Hubble frame: **0.00°**. Scale: an even 2.43× downsample. Chandra built the composite straight on the Hubble press frame.
- Fitted WCS: 0.0974″/px and a 4.16′ field, while the fact sheet says 2.5′. Residuals are 0.03″ RMS.
- `toasty tile-study --fits-wcs sample_2018_m16_wcs.fits m16.tif` gave CenterX/Y 274.7181/−13.8378 and Rotation −34.98°. The catalogue's own Hubble Pillars imageset has Rotation −34.98°.
- The real layer gain here is 2.4×. The CSV shows 1.46× because it relies on the wrong fact-sheet scale.

**Seed WCS from the fact sheet.** I checked the 381 images that carry full AVM WCS:

- 70% are north-up within 1°, and 81% within 5°.
- The fact-sheet "Image is N arcmin across" is within 10% of the AVM scale for 65% of them, and within 25% for 74%.
- RA/Dec plus "Scale" with a north-up assumption is therefore a good *starting guess* for astrometry.net or a registration search. It is not reliable enough to use as the final WCS.

**Catalogue band labels.** The WWT tiles for Crab (`Chandra-335`) and M82 (`Chandra-320`) are visibly multi-band composites. The bandpass work had filed them under `sky__xray.xml`, because the WTML `Credits` strings are truncated to the X-ray credit. Overall, **109 catalogue entries filed as X-ray-only have a composite credit on their Chandra page** (`catalog_band_check`). This should go back to the `bandpass-cleanup` branch. 14 entries go the other way: they are multi-band in the catalogue, but the credit is X-ray only. Those probably point at the wrong panel.

## Biggest wins

1. **The 42 easy new releases, ready to tile now with `toasty tile-study --avm`.** Examples are `2018/crab`, `2018/e0102`, `2018/ring`, `2022/ngc3293`, `2025/casa`, `2026/m101` (8999×9011), `2026/m87` and `2026/sgrae`. Filter the CSV on `set=a, avm_level=full WCS`.
2. **The largest new images.** All need registration except `2026/m101`, which has full AVM:

   | Release | Size |
   | --- | --- |
   | `2023/archives` | 14112×9000 (127 Mpix) |
   | `2025/xa` | 11367×7658 |
   | `2023/3c297` | 11281×6858 |
   | `2026/m101` | 8999×9011 |
   | `2026/30dor` | 8999×8965 |
   | `2025/bone` | 8240×7922 |
   | `2026/kepler` | 7199² |

3. **Composites where the full-res layer is several times sharper** (set a / set b), with the reference to use:

   | Composite | Gain | Reference |
   | --- | --- | --- |
   | M31 `2025/m31`, `2007/m31`, `2013/m31` | 6–30× | PHAT `heic1502a` 69536×22230 (partial coverage); NOIRLab M31 mosaic |
   | 30 Dor `2025/30dor`, `2012/30dor` | 5–12× | `heic1206a` 20323×16259 |
   | M81 `2008/m81` | 6.7× | `heic0710a` 22620×15200 |
   | Omega Cen `2023/spiders` | 6.7× | `heic2409a` 13719² |
   | UHZ1 `2023/uhz1` | 6.7× | JWST Pandora's Cluster |
   | Helix `2025/helix` | 4.9× | `heic0307a` 8000² |
   | Cas A `2024/casa`, `2019/firstlight`, `2005/casa`, `2011/casa` | 3–4× | `heic0609a`; JWST `weic2330a` |
   | M51 `2007/m51`, `2014/m51`, `2018/m51` | 3–4× | `heic0506a` |
   | Rosette `2010/rosette` | 3.7× | DECam `noirlab2424a` 21057×17915 |
   | NGC 2264 `2023/ngc2264` | 3.6× | `noao-04493` |
   | NGC 3293 `2022/ngc3293` | 3.4× | `eso1422a` |
   | Cen A `2023/cena` | 3.4× | `eso1221a` |
   | NGC 1232 `2013/ngc1232` | 2.8× | ESO |
   | M101 `2012/m101` | 2.6× | `opo0907i` |
   | Abell 2744 `2011/a2744` | 2.2× | `heic1111b` |
   | M106 `2014/m106` | 2.2× | `heic1302a` |
   | Sombrero `2007/sombrero` | 2.0× | `heic2506a` |
   | 30 Dor JWST `2023/30dor` | 2.4× | `weic2212a` |

   Many of these references are already WWT imagesets. That allows a cheaper option: tile only Chandra's X-ray layer (`*_xray.tif`) and show it over the existing imageset.

4. **Re-tiling catalogue entries whose current TIFF is sharper than what WWT holds** (≥ 1.4×, same field; AVM present for most). The gain is in brackets:
   - `2008/m81` (4.7×)
   - `2007/sn87a` (3.4×)
   - `2015/iyl` (3.0×)
   - `2010/bppsc` (2.8×)
   - `2012/phoenix` (2.3×)
   - `2012/casa` (2.1×)
   - `2008/dgtau` (2.0×)
   - `2014/msh11g327`, `2007/puppis`, `2013/igr`, `2014/perseusvirgo`, `2010/2gal` (2.0×)
   - `2004/c153` (1.8×)
   - `2008/snr0509` (1.7×)
   - `2016/frontier` (1.6×)
   - `2012/sgra`, `2011/carina`, `2001/cdfn`, `2010/4c0058`, `2017/geminga` (1.4–1.5×)

   (`2008/g19` shows 11×, but its catalogue row maps to the wrong panel. Check it first.)
5. **openFITS (38 catalogue images).** These have Chandra's per-band FITS with WCS, so the X-ray layer can be rebuilt at native resolution and registered exactly.

**The limit on gains.** Most Chandra composites already use the other layer near press resolution: the median layer gain over all matched composites is about 1×. The recompositing win is concentrated in about 40 images, mostly large nearby galaxies and SNRs with Hubble, JWST or DECam mosaics. The X-ray layer itself stays at Chandra's ~0.5″ resolution, so higher-resolution layers only sharpen the context.

## Proposed workflow

1. **Feed scaffolding.** Add `corepipe/chandra.py`, a new `ImageSource` alongside the existing `djangoplicity` and `astropix` sources:
   - `query_candidates` reads the `/photo/YYYY/` index pages.
   - `fetch_candidate` downloads the TIFF, the per-band `_xray`/`_optical` TIFFs and the fact sheet. Reuse `scripts/cxcrawl.py`.
   - `process` uses the image's AVM if `Spatial` is full. Otherwise it reads a sidecar `feeds/chandra/wcs/<id>.fits` made in step 3.

   The feed config is `feeds/chandra/corepipe-config.yaml`, with `feed_id: chandra` and the license from the Chandra image use policy (public domain unless noted).
2. **Easy rows.** Run `toasty tile-study --avm` as usual, then follow the existing catalogue-update runbook: text cleanup, `index.wtml` with https URLs, `cattool ingest`, `emit`, and the manual Azure upload. Set `BandPass` and `Xbands` from the parsed `bands` column.
3. **Medium rows (registration).**
   - **Reference.** Prefer, in order: the verified press image (`fullres_match_url`, whose AVM comes from `/api/json/`); a WWT imageset's source image; or survey or archive FITS: PS1 cutouts, SDSS, IRSA SEIP/AllWISE, MAST HAP for HST, MAST i2d for JWST, or Legacy Survey. Fetch FITS with `astroquery`, cut to the fact-sheet field ×1.5.
   - **Register.** Run `scripts/register_sample.py` against the Chandra composite or, better, its optical/IR layer TIFF: SIFT, RANSAC similarity, then `fit_wcs_from_points`. It writes a header-only WCS FITS. Seed the scale from the fact sheet. Accept a fit with at least 50 inliers and RMS under 0.5 composite pixels, and send the rest to step 4.
   - **Tile.** `toasty tile-study --fits-wcs <id>_wcs.fits image.tif`. Spot-check in `toasty view` or the webclient over the reference imageset.
   - **Catalogue rows.** For set-`b` rows without WCS, convert the WWT placement (CenterX/Y, Rotation, BaseDegreesPerTile, TileLevels, Offset) into a WCS for the current TIFF. Only do this where `wwt_vs_current_res` is about 1 and `wwt_sep_arcmin` is about 0, meaning the same pixel grid; otherwise register.
4. **Hard rows.**
   - **X-ray-only images** have few point sources and no optical stars. Build a reference image from the Chandra Source Catalog / CDA for the listed Obs IDs, either a CSC 2.1 stacked image (FITS with WCS) or the merged event file binned to an image. Then register as in step 3.
   - **Composites with only radio, IXPE or amateur layers.** Install `astrometry.net` (WSL or local index files 4100/5200), then run `solve-field --ra --dec --radius --scale-low/high` seeded from the fact sheet (±30%) on a star-rich layer.
   - Keep whatever fails for manual work in `toasty`/WWT by eye.
5. **Recompositing with full-res layers.** For the gain ≥ 2 list:
   - **Option A (cheap).** Tile only Chandra's `*_xray.tif` with its WCS, and present it as a second imageset over the existing or new full-res Hubble/JWST/DECam imageset. WWT layers it with opacity.
   - **Option B (one-image product).** Reproject the X-ray layer onto the full-res reference grid with `reproject.reproject_interp`. Screen-blend it using Chandra's colour code from `Color Code` in the fact sheet. Tile the result. If the result is gigapixel, use the oversize-TIFF path from the catalogue-update skill.
   - **Credits.** Give each rebuilt composite a new credit naming both sources, and set `Xbands` to all bands.
6. **Catalogue fixes found on the way.** Feed the 109 composites filed as X-ray-only back to `bandpass-cleanup`. Re-map the 10 set-`b` rows with `wwt_sep_arcmin` > 1 to the right `more.html` panel.

## Caveats

- **Name search can miss layers.** The press-image lookup searches djangoplicity sites by name. STScI-only releases not mirrored on esahubble.org, and Spitzer press images, were not looked up. Their rows fall back to "archive FITS (unverified)".
- **Approximate footprints.** Footprints of WWT imagesets are estimated from `BaseDegreesPerTile`. Partial coverage is flagged as `(partial)` or `(small crop only)`.
- **Set a covers main images only.** The `more.html` panels, often an X-ray-only version plus wide-field context images, still have to be triaged per release.
- **Reproducing the CSV.** `scripts/` holds the crawler (`run_crawl.py` → `crawl.json`), the parser and analysis (`analyze.py`), and the registration sample. They need a cache directory as their first argument. HTTP responses are cached there.
