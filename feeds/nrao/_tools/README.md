# public.nrao.edu inventory tools (2026-11)

AstroPix no longer receives NRAO images, so these scripts crawl public.nrao.edu directly.
Use the wwt env python with `-I`. `WORK` is a scratch directory.

1. Fetch the sitemaps into `WORK`: `gallery-item-sitemap.xml`, `gallery-item-sitemap2.xml`
   and `release-sitemap.xml` (all at `https://public.nrao.edu/`). Then write
   `WORK/gallery_items.tsv` (`lastmod<TAB>url` per gallery item).
2. `crawl_gallery.py WORK` writes `gallery.json` (title, datePublished, categories, download
   table). `crawl_releases.py WORK` writes `releases.json` (datePublished, inline images,
   captions).
3. Build a JSON list of `{img: url, ...}` and run `probe_avm.py in.json out.json`. It
   range-fetches the head and tail 4 MB of each file and parses the `avm:Spatial.*` XMP.
4. `build_inventory.py ROOT OUT` (with WORK = ROOT/dl and probe outputs saved as `ROOT/dl/probe_out_{rel,gallery}.json`) holds the hand-curated ready / manual lists and writes
   `inventory-YYYY-MM.json`. It also reads image sizes from the `ROOT/thumbs/` contact-sheet
   cache.

Both crawls take about 15 minutes each at four parallel requests.
