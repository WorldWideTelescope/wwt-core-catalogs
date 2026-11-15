# Hubble images that exist only on NASA's sites (assessment, 2026-11-15)

The question: which Hubble images are published only on science.nasa.gov / www.nasa.gov,
typically "Processing: Gladys Kober (NASA/Catholic University of America)", and could
WWT use them? Nothing has been fetched or tiled.

## What's there

| Source | Images | Notes |
|---|---|---|
| Hubble Caldwell catalogue pages (science.nasa.gov) | 86 objects; **40 Kober-processed** | `catalog_pages.tsv` |
| Hubble Messier catalogue pages | 89 objects; **24 Kober-processed** | `catalog_pages.tsv` |
| www.nasa.gov image articles crediting Kober | **12 found** (2024–2026) | `kober_nasagov.tsv`. WordPress search only matches titles, so this undercounts the weekly images (probably 100+ since 2022). |
| science.nasa.gov "asset" records (STScI releases) | 4,362 | `stsci_assets_science_nasa_gov.tsv`; none credit Kober. These are STScI press releases, mostly also on esahubble.org. |

Largest offered sizes are about 1,000–5,250 px wide for the Kober images (the
`wp-content/uploads` originals), and up to ~9k px for STScI assets.

## Astrometry

- No AVM or WCS in the files checked. The Kober JPEG (HH 80) has no XMP at all; the
  STScI release JPEG (NGC 4449) has XMP but no `avm:Spatial.*`.
- The STScI asset records do carry a seed: object RA/Dec, "Image is 5.1 arcmin across",
  instrument and filters (`acf` in the WP REST API, see `nasa_stma.py`).
- The Kober pages give an object name (Caldwell/Messier number), so a seed position
  comes from Sesame; the field size is not stated.

## Proposed route

Register each image the way the Chandra feed does (`feeds/chandra/_assessment/scripts/register.py`):
seed from the object position and a scale guess (ACS/WFC 0.05"/px, WFC3/UVIS 0.04",
WFPC2 0.1", then resampling), match stars against Legacy Survey / PS1 / DSS2, and accept
only fits that pass the scale, centre and DSS-overlap checks. Hubble fields usually
have plenty of stars, so the yield should be much better than Chandra's X-ray-only
fields. Before fetching, drop anything that duplicates an esahubble/STScI image
already in WWT (same field and scale).

A complete inventory of the weekly images needs a crawl of www.nasa.gov image
articles in the Hubble category (content, not search), or the NASA Hubble Flickr
account, whose photo ids appear in the upload file names (e.g. `55606049603-e8822462fe-o.jpg`).
