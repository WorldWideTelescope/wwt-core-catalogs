import sys, os, re, json, math, csv
sys.path.insert(0, os.path.dirname(__file__))
import cxcrawl as c
import djsearch as dj
from credits import parse_credit, AVAIL
from concurrent.futures import ThreadPoolExecutor

S = sys.argv[1]
OUT = sys.argv[2]
crawl = json.load(open(os.path.join(S, 'crawl.json')))
cat = json.load(open(os.path.join(S, 'catalog_chandra.json')))
allsets = json.load(open(os.path.join(S, 'catalog_all.json')))
pages = crawl['pages']
rows_b = crawl['rows_b']

# ---- openFITS membership
openfits = {}
for f in ['of_xray_data.html', 'of_multiwavelength_data.html']:
    h = open(os.path.join(S, 'web', f), encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'href="/photo/(\d{4}/[^/]+)/(?:fits/)?([^"]+\.(?:fits|fits\.gz|zip))"', h):
        rel = m.group(1)
        if rel.endswith('/archives') or rel.split('/')[1] == 'archives':
            continue
        openfits.setdefault(rel, set()).add(m.group(2))
    for m in re.finditer(r'href="/photo/(\d{4})/archives/fits/([^/]+)/', h):
        openfits.setdefault(f'{m.group(1)}/archives:{m.group(2)}', set()).add('archives')

# ---- catalogue cross-match index (non-Chandra sky imagesets)
DOM = [('esahubble.org', 'Hubble'), ('hubblesite.org', 'Hubble'), ('eso.org', 'ESO'), ('noirlab.edu', 'NOIRLab'),
       ('noao.edu', 'NOIRLab'), ('gemini.edu', 'Gemini'), ('spitzer.caltech.edu', 'Spitzer'), ('esawebb.org', 'JWST'),
       ('webbtelescope.org', 'JWST'), ('wise', 'WISE'), ('nrao.edu', 'VLA/NRAO'), ('galex', 'GALEX'), ('astron.nl', 'LOFAR'),
       ('esa.int', 'ESA')]
xidx = []
for e in allsets:
    if e.get('DataSetType') != 'Sky' or e.get('Projection') != 'Tan':
        continue
    cu = e.get('CreditsUrl') or ''
    if 'chandra.harvard.edu' in cu:
        continue
    mis = next((m for d, m in DOM if d in cu), None)
    if not mis:
        continue
    try:
        bdt = float(e['BaseDegreesPerTile']); L = int(e['TileLevels'])
        xidx.append({'mission': mis, 'name': e.get('Name'), 'ra': float(e['CenterX']), 'dec': float(e['CenterY']),
                     'span_arcmin': bdt * 60, 'px_arcsec': bdt / (256 * 2 ** L) * 3600, 'url': cu})
    except Exception:
        pass


def catalog_xmatch(ra, dec, fov=None):
    out = {}
    for x in xidx:
        s = dj.sep_arcmin(ra, dec, x['ra'], x['dec'])
        if fov and x['span_arcmin'] * 0.75 < 0.5 * fov:
            continue  # too small to stand in for the composite's layer
        if s < x['span_arcmin'] / 2 * 0.8:
            b = out.get(x['mission'])
            if b is None or x['px_arcsec'] < b['px_arcsec']:
                out[x['mission']] = dict(x, sep=s)
    return out


# ---- helpers
def parse_coords(s):
    m = re.search(r'RA\s*(\d+)h\s*(\d+)m\s*([\d.]+)s\s*\|\s*Dec\s*([+\-−]?)\s*(\d+)\D+(\d+)\D+([\d.]+)', s or '')
    if not m:
        return None
    ra = (int(m.group(1)) + int(m.group(2)) / 60 + float(m.group(3)) / 3600) * 15
    sg = -1 if m.group(4) in ('-', '−') else 1
    dec = sg * (int(m.group(5)) + int(m.group(6)) / 60 + float(m.group(7)) / 3600)
    return ra, dec


def parse_scale(s):
    s = (s or '').replace('´', "'")
    m = re.search(r'([\d.]+)\s*(?:by|x|×)\s*([\d.]+)\s*(arcmin|arcsec|deg|degrees?)', s, re.I)
    if m:
        v = float(m.group(1)); u = m.group(3).lower()
    else:
        m = re.search(r'([\d.]+)\s*(arcmin|arcsec|arc ?min|arc ?sec|deg|degrees?|\')', s, re.I)
        if not m:
            return None
        v = float(m.group(1)); u = m.group(2).lower().replace(' ', '')
    if u.startswith('arcsec'): return v / 60
    if u.startswith('deg'): return v * 60
    return v


def tofl(x):
    return float(re.sub(r'[^0-9eE+\-.]', '', str(x)))


def mb(n):
    return round(n / 1e6, 1) if n else ''


def dimstr(d):
    return f'{d[0]}x{d[1]}' if d else ''


LAYER_SUFFIX = re.compile(r'_(xray|x-ray|optical|opt|ir|infrared|radio|uv|halpha|ha|hst|spitzer|jwst|chandra|nustar|ixpe|xmm|alma|vla|meerkat)\b', re.I)

# ---- build per-image records
records = []
for p in crawl['probes']:
    sset, idx = p['key'].split('|', 1)
    R = pages.get(p['rel'], {})
    facts = R.get('facts', {})
    rec = {'set': sset, 'release': p['rel'], 'release_url': R.get('url') or f'https://chandra.harvard.edu/photo/{p["rel"]}/'}
    t = R.get('title', '')
    t = re.sub(r'^Chandra :: Photo Album :: ', '', t)
    rec['title'] = re.sub(r'\s*::.*$', '', t).strip()
    rec['release_date'] = facts.get('Release Date', '')
    rec['category'] = facts.get('Category', '')
    if sset == 'b':
        rb = rows_b[int(idx)]
        ce = cat[rb['cat_idx']]
        rec['img_source'] = rb.get('img_source', 'main')
        rec['wwt_name'] = ce.get('Name')
        rec['wwt_file'] = os.path.basename(ce['_file'])
        rec['wwt_bands'] = ce.get('Xbands') or ce.get('BandPass')
        rec['astropix_id'] = ce.get('Xastropix_ids', '')
        rec['credits_url'] = ce.get('CreditsUrl')
        try:
            rec['wwt_px_arcsec'] = float(ce['BaseDegreesPerTile']) / (256 * 2 ** int(ce['TileLevels'])) * 3600
            rec['wwt_ra'], rec['wwt_dec'] = float(ce['CenterX']), float(ce['CenterY'])
        except Exception:
            pass
        rec['wwt_tiles'] = ce['Url']
        wl = parse_credit(ce.get('Credits', ''))
        rec['_wwt_comp'] = any(m != 'Chandra' for _, _, m in wl)
    else:
        rec['img_source'] = 'main'
    files = p['files']
    pr = p['probe']
    rec['image_file'] = files.get('tif') or files.get('lg') or files.get('jpg') or ''
    # AVM
    avm_from = [k for k in ('tif', 'jpg', 'lg', 'k4') if pr.get(k, {}).get('avm')]
    wcs_from = [k for k in ('tif', 'jpg', 'lg', 'k4') if pr.get(k, {}).get('wcs')]
    rec['avm_present'] = 'yes' if avm_from else 'no'
    rec['avm_wcs'] = 'yes' if wcs_from else ('no' if not avm_from else 'no (AVM without Spatial)')
    rec['avm_in'] = ','.join(wcs_from or avm_from)
    pos_from = [k for k in ('tif', 'jpg', 'lg', 'k4') if pr.get(k, {}).get('Spatial.ReferenceValue')]
    rec['avm_level'] = 'full WCS' if wcs_from else 'position only' if pos_from else 'no Spatial tags' if avm_from else 'none'
    if not wcs_from and pos_from:
        rec['avm_in'] = ','.join(pos_from)
    wsrc = pr[wcs_from[0]] if wcs_from else None
    if wsrc:
        rec['avm_quality'] = (wsrc.get('Spatial.Quality') or [''])[0]
    # FITS
    fl = sorted(set(os.path.basename(x) for x in R.get('fits_links', [])))
    of = openfits.get(p['rel'])
    rec['fits'] = 'openFITS' if of else ('release page' if fl else 'no')
    rec['fits_files'] = ';'.join(sorted(of)[:8]) if of else ';'.join(fl[:8])
    # sizes
    sizes = []
    for k in ('tif', 'lg', 'k4', 'jpg'):
        q = pr.get(k)
        if q and q.get('dims') and not q.get('missing'):
            sizes.append((q['dims'][0] * q['dims'][1], k, q))
    sizes.sort(key=lambda x: -x[0])
    if sizes:
        _, k, q = sizes[0]
        rec['largest_px'] = dimstr(q['dims'])
        rec['largest_file'] = files[k]
        rec['largest_mpix'] = round(sizes[0][0] / 1e6, 1)
        rec['largest_bytes_MB'] = mb(q.get('bytes'))
    tq = pr.get('tif')
    rec['tif_available'] = 'yes' if tq and not tq.get('missing') else 'no'
    # separate per-band layer files offered by Chandra
    dl = [h for h, _ in R.get('downloads', [])] + [b.get('tif') or '' for b in R.get('more', [])]
    lay = sorted(set(h for h in dl if h and LAYER_SUFFIX.search(h) and re.search(r'\.tiff?$', h, re.I)))
    rec['chandra_layer_tifs'] = ';'.join(lay)
    # placement & field
    W = sizes[0][2]['dims'] if sizes else None
    ra = dec = None; fov = None; px = None
    if wsrc and wsrc.get('Spatial.ReferenceValue'):
        ra, dec = [tofl(x) for x in ' '.join(wsrc['Spatial.ReferenceValue']).replace(';', ' ').split()[:2]]
        try:
            sc = abs(tofl(wsrc['Spatial.Scale'][0]))
            rd = [tofl(x) for x in wsrc.get('Spatial.ReferenceDimension', [])] or None
            if rd:
                fov = rd[0] * sc * 60
            elif W:
                fov = W[0] * sc * 60
        except Exception:
            pass
    if ra is None and rec.get('wwt_ra') is not None:
        ra, dec = rec['wwt_ra'], rec['wwt_dec']
    if ra is None:
        cc = parse_coords(facts.get('Coordinates (J2000)', ''))
        if cc:
            ra, dec = cc
    if fov is None:
        fov = parse_scale(p.get('scale') or facts.get('Scale', ''))
    if fov and W:
        px = fov * 60 / W[0]
    rec['ra'] = round(ra, 5) if ra is not None else ''
    rec['dec'] = round(dec, 5) if dec is not None else ''
    rec['fov_arcmin'] = round(fov, 2) if fov else ''
    rec['composite_px_arcsec'] = round(px, 4) if px else ''
    if rec.get('wwt_px_arcsec') and px:
        rec['wwt_vs_current_res'] = round(rec['wwt_px_arcsec'] / px, 2)
    # layers
    credit = p.get('credit') or facts.get('Credit', '')
    rec['credit'] = credit
    layers = parse_credit(credit)
    non = [(b, s, m) for b, s, m in layers if m != 'Chandra']
    rec['composite'] = 'composite' if non else 'single-band'
    if sset == 'b':
        wb = rec.get('wwt_bands') or ''
        pb = [b for b in dict.fromkeys(b for b, _, _ in layers) if b]
        if non and wb in ('XRay', 'None', ''):
            rec['catalog_band_check'] = 'catalogue XRay-only, page credit is composite (' + ','.join(pb) + ')'
        elif not non and ',' in wb:
            rec['catalog_band_check'] = 'catalogue multi-band, page credit is X-ray only (verify image variant)'
        else:
            rec['catalog_band_check'] = 'consistent'
        if rec.get('wwt_ra') is not None and ra is not None:
            rec['wwt_sep_arcmin'] = round(dj.sep_arcmin(ra, dec, rec['wwt_ra'], rec['wwt_dec']), 3)
    rec['bands'] = ','.join(dict.fromkeys(b or '?' for b, _, _ in layers))
    rec['layers'] = ' | '.join(f'{b or "?"}: {m} ({s[:60]})' for b, s, m in layers)
    rec['_non'] = non
    rec['_aka'] = facts.get('Also Known As', '')
    rec['_W'] = W
    records.append(rec)

# ---- specific layer lookups on djangoplicity sites (composites only)
jobs = []
for i, r in enumerate(records):
    if r['ra'] == '' or not r['_non']:
        continue
    for b, s, m in r['_non']:
        if m in dj.SITES:
            jobs.append((i, m))
jobs = sorted(set(jobs))
print('layer lookups', len(jobs))


def look(job):
    i, m = job
    r = records[i]
    try:
        return job, dj.best_match(m, float(r['ra']), float(r['dec']), r['fov_arcmin'] or 5, r['title'], r['_aka'])
    except Exception as e:
        return job, []


with ThreadPoolExecutor(6) as ex:
    found = dict(ex.map(look, jobs))

# ---- fill layer columns + effort
XRAYM = {'XMM-Newton', 'eROSITA', 'IXPE', 'NuSTAR', 'ROSAT', 'Swift', 'Fermi'}
FITSWCS = {'Spitzer', 'WISE', '2MASS', 'Pan-STARRS', 'SDSS', 'DSS', 'GALEX', 'Herschel', 'UKIRT', 'Legacy Survey'}
for i, r in enumerate(records):
    xm = catalog_xmatch(float(r['ra']), float(r['dec']), r['fov_arcmin'] or None) if r['ra'] != '' else {}
    notes = []
    verified_ref = []
    best_gain = None
    lay_rows = []
    for b, s, m in r['_non']:
        av, how = AVAIL.get(m, AVAIL['Other'])
        cand = found.get((i, m)) or []
        ent = {'band': b, 'mission': m, 'generic': av}
        F = r['fov_arcmin'] or 0
        big = [x for x in cand if min(x['fov_arcmin']) >= 0.5 * F]
        cand = big or cand
        if cand:
            cbest = cand[0]
            cbest['coverage'] = cbest['coverage'] if big else 0
            ent['match'] = f"{cbest['site']}:{cbest['id']} {cbest['w']}x{cbest['h']} @{cbest['px_arcsec']:.3f}\"/px" + ('' if cbest['coverage'] == 1 else ' (partial)' if cbest['coverage'] else ' (small crop only)')
            ent['match_url'] = cbest['url']
            if r['composite_px_arcsec'] and cbest['px_arcsec'] and big:
                g = r['composite_px_arcsec'] / cbest['px_arcsec']
                ent['gain'] = round(g, 2)
                best_gain = max(best_gain or 0, g)
            if big:
                verified_ref.append(f"{m} press AVM ({cbest['id']})")
        cm = {'ESO': 'ESO', 'Hubble': 'Hubble', 'JWST': 'JWST', 'NOIRLab': 'NOIRLab', 'Gemini': 'Gemini', 'Spitzer': 'Spitzer',
              'WISE': 'WISE', 'VLA/NRAO': 'VLA/NRAO', 'GALEX': 'GALEX', 'LOFAR': 'LOFAR'}.get(m)
        x = xm.get(cm) if cm else None
        if m == 'NOIRLab' and not x:
            x = xm.get('Gemini')
        if x:
            ent['in_wwt'] = f"{x['name']} @{x['px_arcsec']:.3f}\"/px"
            if r['composite_px_arcsec']:
                g = r['composite_px_arcsec'] / x['px_arcsec']
                ent['wwt_gain'] = round(g, 2)
                best_gain = max(best_gain or 0, g)
            verified_ref.append(f"{m} imageset already in WWT")
        if not cand and not x and m in FITSWCS:
            verified_ref.append(f"{m} survey FITS")
        lay_rows.append(ent)
    r['nonchandra_layers'] = ' | '.join(f"{e['band']}:{e['mission']}" for e in lay_rows)
    r['fullres_public'] = ' | '.join(f"{e['mission']}={e['generic']}" for e in lay_rows)
    r['fullres_match'] = ' | '.join(
        f"{e['mission']}: " + '; '.join(v for v in [e.get('match'), ('WWT ' + e['in_wwt']) if e.get('in_wwt') else None] if v)
        for e in lay_rows if e.get('match') or e.get('in_wwt'))
    r['fullres_match_url'] = ' | '.join(e['match_url'] for e in lay_rows if e.get('match_url'))
    gains = [g for e in lay_rows for g in (e.get('gain'), e.get('wwt_gain')) if g]
    r['layer_res_gain'] = round(max(gains), 2) if gains else ''
    r['fullres_vs_chandra_layer'] = ' | '.join(
        f"{e['mission']} x{max(g for g in (e.get('gain'), e.get('wwt_gain')) if g):.1f}" for e in lay_rows if e.get('gain') or e.get('wwt_gain'))
    # alignment effort
    if r['avm_wcs'] == 'yes':
        eff, basis = 'easy', 'AVM WCS in Chandra image'
    elif r['fits'] != 'no':
        eff, basis = 'easy', 'Chandra FITS (WCS)'
    elif verified_ref:
        eff, basis = 'medium', 'register against ' + verified_ref[0]
    elif [m for _, _, m in r['_non'] if AVAIL.get(m, ('',))[0] == 'yes' and m not in XRAYM]:
        m0 = [m for _, _, m in r['_non'] if AVAIL.get(m, ('',))[0] == 'yes' and m not in XRAYM][0]
        eff, basis = 'medium', f'register against {m0} archive FITS ({AVAIL[m0][1].split(";")[0]}) - match not yet verified'
    elif r['set'] == 'b' and r.get('wwt_ra') is not None:
        eff, basis = 'medium', 'reuse existing WWT placement (verify pixel grid matches)'
    else:
        eff, basis = 'hard', 'plate-solve (astrometry.net, seed from fact-sheet RA/Dec + scale)' if r['composite'] == 'composite' \
            else 'X-ray only: register to CSC/CDA image of listed ObsIDs, or astrometry.net seeded from fact sheet'
    if r['set'] == 'a' and r['ra'] != '':
        F = max(r['fov_arcmin'] or 3, 1)
        near = []
        for ce in cat:
            try:
                s = dj.sep_arcmin(float(r['ra']), float(r['dec']), float(ce['CenterX']), float(ce['CenterY']))
            except Exception:
                continue
            if s < F / 2:
                y = re.search(r'/photo/(\d{4})/', ce['CreditsUrl'])
                near.append(f"{ce.get('Name')} ({y.group(1) if y else '?'})")
        r['existing_chandra_in_wwt'] = '; '.join(dict.fromkeys(near))[:300]
    r['alignment_effort'] = eff
    r['alignment_basis'] = basis

cols = ['set', 'release', 'title', 'release_date', 'img_source', 'image_file', 'wwt_name', 'wwt_file', 'wwt_bands', 'astropix_id',
        'avm_present', 'avm_level', 'avm_in', 'avm_quality', 'fits', 'fits_files', 'tif_available', 'largest_px', 'largest_mpix',
        'largest_bytes_MB', 'largest_file', 'chandra_layer_tifs', 'ra', 'dec', 'fov_arcmin', 'composite_px_arcsec', 'wwt_px_arcsec',
        'wwt_vs_current_res', 'wwt_sep_arcmin', 'catalog_band_check', 'composite', 'bands', 'layers', 'nonchandra_layers', 'fullres_public', 'fullres_match',
        'fullres_vs_chandra_layer', 'layer_res_gain', 'fullres_match_url', 'alignment_effort', 'alignment_basis', 'existing_chandra_in_wwt', 'credit',
        'release_url', 'credits_url', 'wwt_tiles']
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
    w.writeheader()
    for r in records:
        rr = dict(r)
        if isinstance(rr.get('wwt_px_arcsec'), float):
            rr['wwt_px_arcsec'] = round(rr['wwt_px_arcsec'], 4)
        w.writerow(rr)
json.dump([{k: v for k, v in r.items() if not k.startswith('_')} for r in records], open(os.path.join(S, 'records.json'), 'w'), indent=1, default=str)
print('wrote', len(records))
