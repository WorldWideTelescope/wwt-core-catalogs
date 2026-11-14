import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
import cxcrawl as c
from concurrent.futures import ThreadPoolExecutor

S = sys.argv[1]
BASE = 'https://chandra.harvard.edu'

# ---- set (a): releases 2018..2026
rels_a = []
for y in range(2018, 2027):
    d, _ = c.fetch(f'{BASE}/photo/{y}/')
    h = d.decode('utf-8', 'replace')
    found = []
    for m in re.finditer(r'href="(?:https?://chandra\.harvard\.edu)?/photo/%d/([A-Za-z0-9_\-]+)/(?:index\.html)?"' % y, h):
        r = f'{y}/{m.group(1)}'
        if r not in found:
            found.append(r)
    rels_a += found
print('set a releases', len(rels_a))

# ---- set (b): catalogue entries
cat = json.load(open(os.path.join(S, 'catalog_chandra.json')))
rows_b = []
for e in cat:
    cu = e['CreditsUrl']
    m = re.search(r'chandra\.harvard\.edu/photo/(\d{4}/[^/#?]+)/?([^#]*)(?:#(.*))?', cu)
    anc = m.group(3) or ''
    mi = re.match(r'img(\d+)[a-z]?$', anc)
    rows_b.append({'rel': m.group(1), 'page': m.group(2), 'imgn': int(mi.group(1)) if mi else None,
                   'anchor': anc if anc and not mi else None, 'cat': e})
rels_b = sorted(set(r['rel'] for r in rows_b))
print('set b releases', len(rels_b))

allrels = sorted(set(rels_a) | set(rels_b))
with ThreadPoolExecutor(6) as ex:
    pages = dict(zip(allrels, ex.map(c.parse_release, allrels)))


def pick_main(R):
    tif = lg = jpg = k4 = None
    for href, t in R.get('downloads', []):
        tl = t.lower()
        if tl.startswith('tif') and '(' in tl and not tif: tif = href
        elif tl.startswith('large jpeg') and not lg: lg = href
        elif tl.startswith('jpeg (') and not jpg: jpg = href
        elif tl.startswith('4k') and not k4: k4 = href
    if not tif:
        for href, t in R.get('downloads', []):
            if re.search(r'\.tiff?$', href, re.I): tif = href; break
    return {'tif': tif, 'lg': lg, 'jpg': jpg, 'k4': k4}


jobs = []  # (key, rel, files, credit, scale, extra)
for rel in rels_a:
    R = pages[rel]
    f = pick_main(R)
    jobs.append(('a|' + rel, rel, f, R.get('facts', {}).get('Credit', ''), R.get('facts', {}).get('Scale', '')))
for i, rb in enumerate(rows_b):
    R = pages[rb['rel']]
    f = pick_main(R)
    credit = R.get('facts', {}).get('Credit', '')
    scale = R.get('facts', {}).get('Scale', '')
    rb['img_source'] = 'main'
    if rb.get('anchor') and R.get('more'):
        for b in R['more']:
            if b.get('tif') and rb['anchor'].lower() in b['tif'].lower():
                f = {'tif': b['tif'], 'lg': None, 'jpg': b['jpg'], 'k4': None}
                if b['credit']: credit = b['credit']
                if b['scale']: scale = b['scale']
                rb['img_source'] = 'more#' + rb['anchor']
                break
    elif rb['imgn'] and R.get('more'):
        k = rb['imgn'] - 1
        if k < len(R['more']):
            b = R['more'][k]
            f = {'tif': b['tif'], 'lg': None, 'jpg': b['jpg'], 'k4': None}
            if b['credit']: credit = b['credit']
            if b['scale']: scale = b['scale']
            rb['img_source'] = f'more#img{rb["imgn"]}'
    jobs.append((f'b|{i}', rb['rel'], f, credit, scale))


def do(job):
    key, rel, f, credit, scale = job
    base = f'{BASE}/photo/{rel}/'
    out = {'key': key, 'rel': rel, 'files': f, 'credit': credit, 'scale': scale, 'probe': {}}
    for k in ('tif', 'lg', 'jpg', 'k4'):
        if f.get(k):
            out['probe'][k] = c.probe(base + f[k], 'tif' if k == 'tif' else 'jpg')
    return out


with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(do, jobs))

json.dump({'pages': pages, 'rels_a': rels_a, 'rows_b': [dict({k: v for k, v in r.items() if k != 'cat'}, cat_idx=i) for i, r in enumerate(rows_b)], 'probes': res},
          open(os.path.join(S, 'crawl.json'), 'w'), indent=1, default=str)
print('done', len(res))
