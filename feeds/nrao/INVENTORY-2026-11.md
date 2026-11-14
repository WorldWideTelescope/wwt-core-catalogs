# NRAO feed inventory, 2026-11

Releases at public.nrao.edu since the last feed run (newest `Xastropix_ids="nrao|…"` entries
date from 2019), checked for usable astrometry. Machine-readable version:
[`inventory-2026-11.json`](inventory-2026-11.json). The crawl and probe scripts are in
[`_tools/`](_tools/).

**Result: most releases lack astrometry, so this run stops at the inventory (no tiling, no
WTMLs).** Five images have complete AVM and could be tiled right away. Another 45 are clean
observational sky images that would each need manual alignment.

## Why the configured source finds nothing

`corepipe-config.yaml` reads NRAO through AstroPix (`astropix.org/link/c60`). That feed still
answers, but it holds only the same 34 pre-2019 records that are already in `imagesets/`.
NRAO stopped submitting to AstroPix around 2019, so `pipeline.py refresh` will never see a new
NRAO image. A future NRAO source would need a public.nrao.edu crawler like `_tools/`.

## What was searched

| Source | Total | Published 2019-06 or later | Image files probed |
|---|---|---|---|
| Gallery items (`gallery-item-sitemap*.xml`) | 1,154 | 221 | 166 (Original TIFF + Hi-Res) |
| News releases (`release-sitemap.xml`) | 979 | 402 | 666 (inline images, site chrome removed) |

Each file was range-fetched (first and last 4 MB) and its XMP parsed for `avm:Spatial.*`.

| AVM state | Release images | Gallery files |
|---|---|---|
| No XMP at all | 303 | 92 |
| XMP but no Spatial tags | 318 | 64 |
| Partial Spatial (no Scale, or a component's dimensions) | 26 | 6 |
| "Full" Spatial | 16 | 4 |

The 20 "full" files come down to **5 usable images**. The rest were set aside:

- Placeholder WCS (RA/Dec 0,0, dimensions 1×1), all from the 2026 releases:
  `PJ0846_15_layout`, `Wolf_Rayet_SNR_FINAL`, `Faisst_Galaxy_Panels`, `3c84deep-Blue-Red`.
- Copies of other publishers' releases: `eso2603a` and `eso25xxa-ACES` (ESO ACES Central
  Molecular Zone mosaic), `eso2316a` (ESO), `webb.jpg` (JWST SMACS 0723), `noirlab2619a` (Rubin;
  excluded by the Rubin full-field rule).
- `nrao22ao17` (HL Tau, 2022 reissue) duplicates `eso1436a`. `nrao23jm01_HLTau_Polarization_Illustration`
  is an illustration whose WCS doesn't match its pixel size.
- `SgrA_Radio_Circle` has an EHT inset annotation, and its AVM describes a 3600² component
  rather than the 7974×4484 image.
- `EHT-Actual-Image` (M87*): the scale is microarcseconds per pixel, far too small to show in WWT.

## Ready to tile (complete AVM, dimensions match the pixels)

| Image | Band | Released | File (`wp-content/uploads/…`) | Catalogue overlap |
|---|---|---|---|---|
| PKS 2014-55 "Double Boomerang" radio galaxy (MeerKAT + DES) | Multi (`Visible,Radio`) | 2020-05-04 | 2020/05/Xgalaxy_composite_02042020_SD.jpg | none |
| Centaurus A inner lobes (VLA) | Radio | 2020-02-14 | 2020/02/CenA_Radio_Red.jpg | eso0005b, eso1222c and Chandra composites show different data: keep |
| M81 group in neutral hydrogen (GBT + VLA) | Radio | 2020-02-26 | 2020/02/m81_radio_only_GBTandVLA.tif | no radio imageset nearby; only 720 px, but covers 3° |
| Host galaxy of FRB 20190520B (VLA + optical) | Multi (`Visible,Radio`) | 2022-06-06 | 2022/06/nrao21df05b.jpg | none |
| Antennae galaxies (ALMA + Hubble) | Multi (`Visible,Radio`) | 2023-03-13 (file from 2018) | 2018/03/AntennaeZoomAllRGB.jpg | **NEAR eso1137a**: same 0.05"/px density, ~19% wider field (4005 vs 3375 px). User decides |

All Multi entries get `Xdominant_band="Radio"`. These five are not ingested anywhere (AstroPix
never had them). Tiling them is quick, but this run's rule was to stop at the inventory.

## Would need manual alignment (45)

All 45 are observational, unannotated, single-panel images. "Partial" means the file has a
reference position and pixel but no scale and/or rotation. In that case only the scale and
rotation need solving. For the tiny ALMA fields (protoplanetary disks, high-z galaxies), no
survey shows anything to match. The practical route there is the public FITS release named
in the Anchor column, rather than aligning the press JPEG.

| # | Released | Object | Pixels | AVM | Anchor imagery | Note |
|---|---|---|---|---|---|---|
| 1 | 2019-06-05 | Sgr A* cool gas ring (ALMA) | 1000x1000 | — | Sgr A* VLBI position + scale from Murchikova et al. 2019 | tiny field (~2") |
| 2 | 2019-09-05 | Galactic Centre radio bubbles (MeerKAT) | 1575x1800 | — | Better: tile the public SARAO MeerKAT GC mosaic FITS (Heywood et al.); else compact sources vs. "Galactic Center 90cm" | |
| 3 | 2019-11-26 | NGC 4631 magnetic ropes (VLA CHANG-ES + optical) | 2560x1584 | — | Field stars vs. DSS2 / SDSS | |
| 4 | 2019-12-11 | MAMBO-9 (ALMA + HST) | 1920x1080 | — | HST COSMOS galaxies in frame | tiny field |
| 5 | 2020-01-05 | NGC 6240 (ALMA + HST) | 1534x1724 | — | Hubble NGC 6240 / PanSTARRS | |
| 6 | 2020-04-28 | Wolfe Disk DLA0817g (ALMA + HST) | 5400x5400 | partial | Scale + rotation from HST galaxies | tiny field |
| 7 | 2020-06-11 | Giant young cluster forming (ALMA + HST mosaic) | 3780x3780 | partial | Stars vs. Gaia DR3 / HST | |
| 8 | 2020-07-13 | RU Lup disk spiral (ALMA) | 3000x3000 | partial | DSHARP / Huang et al. 2020 FITS | tiny field |
| 9 | 2020-07-20 | NGC 4217 magnetic field (VLA + SDSS) | 1173x912 | — | SDSS / DSS2 field stars | |
| 10 | 2020-08-24 | Young stop-and-start radio jets | 1500x1500 | — | Object ID + scale from Nyland et al. 2020, then PanSTARRS | needs object ID |
| 11 | 2020-11-09 | IC 310, Perseus cluster (VLA + optical) | 4866x3114 | — | Field stars vs. PanSTARRS / SDSS | |
| 12 | 2020-11-09 | NGC 1265, Perseus cluster (VLA + optical) | 4464x3132 | — | Field stars vs. PanSTARRS / SDSS | |
| 13 | 2020-11-09 | NGC 1275 / Perseus A (VLA + optical) | 2048x1489 | — | Field stars vs. PanSTARRS / SDSS | |
| 14 | 2021-03-15 | Lensed radio galaxy behind MACS J0717.5+3745 (HST + VLA) | 10350x10350 | — | Hubble Frontier Fields MACS J0717 | |
| 15–17 | 2021-04-26 | W51 e2 / e8 / North protostellar outflows (ALMA), 3 images | 7056x7056 | — | ALMA archive FITS (Goddi et al. 2020) | tiny fields, no stars |
| 18 | 2021-05-03 | W49A star-forming region (VLA + IR) | 4500x4500 | — | Stars vs. 2MASS / Spitzer GLIMPSE | |
| 19 | 2021-06-08 | PHANGS-ALMA NGC 628 | 13000x13000 | — | DSS2 / PanSTARRS stars, or PHANGS-ALMA moment-0 FITS | NEAR `NRAO_Gallery_nrao18cb12d` (2019 NGC 628 composite) |
| 20–27 | 2021-06-07/08 | PHANGS-ALMA NGC 4254, 4321, 1385, 1566, 3351, 3627, 4535, 5248 (8 images) | 7000–14000 px | — | DSS2 / SDSS stars, or PHANGS-ALMA FITS | |
| 28 | 2021-06-17 | Elias 2-27 spiral disk (ALMA) | 1920x1080 | partial | DSHARP FITS | tiny field |
| 29 | 2021-07-21 | GLOSTAR Galactic-plane strip (VLA) | 12500x3200 | — | GLOSTAR FITS, or HII regions vs. GLIMPSE / WISE | |
| 30 | 2021-07-27 | NGC 4921 ram-pressure stripping (HST + ALMA) | 4046x3823 | — | Hubble / SDSS | |
| 31 | 2021-09-13 | HD 163296 in HCN (ALMA MAPS) | 3000x3000 | — | MAPS FITS (Öberg et al. 2021) | tiny field; eso1818a (continuum) already catalogued |
| 32 | 2021-10-25 | VERTICO NGC 4567/4568 (ALMA + HST) | 5080x4572 | — | SDSS / Hubble, or VERTICO FITS | |
| 33 | 2021-10-25 | VERTICO NGC 4254 (ALMA + HST) | 9936x9936 | — | SDSS / Hubble, or VERTICO FITS | NEAR #20 |
| 34 | 2021-10-20 | IC 1613 neutral hydrogen (VLA) | 1771x1771 | — | No stars: needs the HI FITS (LITTLE THINGS) | |
| 35 | 2021-12-06 | M87 jet double helix (VLA) | 3000x1500 | — | Jet knots vs. Hubble / Chandra M87 in catalogue | |
| 36–37 | 2022-04-22 | Post-starburst galaxies 0379 and 0570 (HST + ALMA) | 4137x4508 | — | SDSS IDs from Smercina et al. 2022, then SDSS stars | needs object IDs |
| 38 | 2022-06-03 | A1689-zD1 behind Abell 1689 (ALMA + HST) | 4092x3894 | partial | Hubble Abell 1689 in catalogue | |
| 39 | 2022-06-06 | HD 53143 debris disk (HST + ALMA) | 3000x2600 | partial | Gaia star position + scale from the paper | tiny field |
| 40 | 2022-06-06 | 30 Doradus molecular filaments (HST + ALMA) | 4000x5000 | partial | Hubble 30 Dor in catalogue / Gaia | |
| 41 | 2022-08-25 | SDSS J1448+1010 merger tidal tails (ALMA + optical) | 1000x1000 | — | SDSS / PanSTARRS | |
| 42 | 2023-02-24 | Arp 299 (2023 image) | 3823x3823 | — | Hubble Arp 299 / PanSTARRS | probably duplicates `NRAO_Gallery010` |
| 43 | 2025-03-17 | SPT2349-56 protocluster gas (ALMA + optical/IR) | 2000x1200 | — | HST / JWST archive | confirm it's data, not art |
| 44 | 2026-06-04 | Sgr A* surroundings in CO + X-ray | 3900x3890 | — | Chandra Galactic Centre in catalogue | Multi `XRay,Radio` |
| 45 | 2026-07-09 | Orion Nebula hidden HI shell (VLA + WISE) | 3840x3840 | — | WISE All-Sky in WWT | easiest of the batch; `Infrared,Radio` |

By anchor type:

- **Field stars in a survey WWT already shows** (DSS2, SDSS, PanSTARRS, 2MASS, WISE): 21.
  These are #3, 5, 9, 11–13, 18–27, 30, 32, 33, 41, 45 (#19–27 can alternatively use the
  PHANGS FITS).
- **Existing catalogue imagery** (Hubble / Chandra / Frontier Fields): 7. These are #7, 14,
  35, 38, 40, 42, 44.
- **Public FITS rather than the JPEG** (tiny ALMA fields, HI maps, Galactic Centre/plane):
  12. These are #1, 2, 6, 8, 15–17, 28, 29, 31, 34, 39.
- **Object ID needed first**: 3 (#10, 36, 37). Plus #4 and #43 (HST/JWST galaxies; #43 also
  needs confirmation that it isn't an illustration).

## Skipped, and why

- **Illustrations, animations, posters, diagrams and photos of telescopes or people.** This
  covers most of the 2024–26 releases, which now usually carry a single artist's impression.
  The 2022–23 "desktop background" and VLA astrophotography gallery sets also fall here.
- **Annotated or multi-panel science figures.** Examples: NGC 3258, NGC 1068 (arrows), the
  Phoenix layout, SN 1987A insets, the W49A close-up with insets, MRG-M0138, SPT0311-58,
  Stephan's Quintet ALMA+JWST insets, exoALMA/CAMPOS/sigma Ori disk grids, the ALCHEMI
  NGC 253 panels, WL 20, the GC stellar nurseries, the protostellar jet, Arp 220, the
  Wolf-Rayet SNR and VLASS plots.
- **Sub-arcsecond VLBI/EHT images.** These include M87*, Sgr A*, 3C 279, NGC 1052, blazars,
  CSOs, the 3C 84 ngVLA first-light point source and Antares' surface.
- **Solar-system targets.** Jupiter, Uranus, Saturn, Io, the Moon's Tycho crater, and the
  2I/Borisov and 3I/ATLAS comets.
- **Too small or legacy.** The M33 HI colours image (512 px) and V Hya (448 px).
- **Duplicates.** The M87 ALMA polarisation image (= `eso2105d`), the GW Ori side-by-side
  (`eso2014c` is catalogued), HL Tau (= `eso1436a`), and the V883 Ori water image (`eso1626b`
  covers the object).
- **Other feeds.** JWST (Faisst panels, NIRCam composites, `webb.jpg`), Hubble/STScI (Cloud-9),
  Chandra (Death Star black holes) and NOIRLab (`noirlab2619a`).

## For the ESO feed (not in the catalogue yet)

NRAO re-hosts these ESO releases. Their originals and AVM live at eso.org:
`eso2603` (ACES ALMA mosaic of the Central Molecular Zone, 2026; WCS present, 92' wide),
`eso2316a` (9io9 magnetic field), `eso2415c`, `eso2205b` (IRS 48), `eso2411a`.
`eso2014c` and `eso1726*` are already catalogued.
