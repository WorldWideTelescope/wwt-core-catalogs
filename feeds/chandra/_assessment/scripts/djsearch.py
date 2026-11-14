import re, json, math, urllib.parse
import cxcrawl as c

SITES = {
    'Hubble': 'https://esahubble.org/images/',
    'JWST': 'https://esawebb.org/images/',
    'ESO': 'https://www.eso.org/public/images/',
    'NOIRLab': 'https://noirlab.edu/public/images/',
    'Gemini': 'https://noirlab.edu/public/images/',
}


def search(site, q, maxn=10):
    url = SITES[site] + '?search=' + urllib.parse.quote_plus(q)
    d, _ = c.fetch(url)
    if not d:
        return []
    h = d.decode('utf-8', 'replace')
    ids = re.findall(r"\bid:\s*'([^']+)'", h)
    out = []
    for i in ids:
        if i not in out:
            out.append(i)
    return out[:maxn]


def fnum(v):
    try:
        return float(v)
    except Exception:
        return None


def info(site, iid):
    d, _ = c.fetch(SITES[site] + urllib.parse.quote(iid) + '/api/json/')
    if not d:
        return None
    try:
        j = json.loads(d)
    except Exception:
        return None
    rv = j.get('Spatial.ReferenceValue') or []
    dim = j.get('Spatial.ReferenceDimension') or []
    sc = j.get('Spatial.Scale') or []
    cd = j.get('Spatial.CDMatrix') or []
    res = {'id': iid, 'site': site, 'url': j.get('ReferenceURL') or SITES[site] + iid + '/',
           'title': str(j.get('Title', ''))[2:-1] if str(j.get('Title', '')).startswith("b'") else j.get('Title'),
           'facility': j.get('Facility'), 'quality': j.get('Spatial.Quality')}
    try:
        res['ra'], res['dec'] = float(rv[0]), float(rv[1])
    except Exception:
        return res
    w = h = None
    try:
        w, h = int(float(dim[0])), int(float(dim[1]))
    except Exception:
        pass
    sx = None
    if sc and fnum(sc[0]):
        sx = abs(fnum(sc[0]))
    elif cd and len(cd) >= 4 and fnum(cd[0]) is not None:
        sx = math.hypot(fnum(cd[0]), fnum(cd[2]))
    # full-size resource dims if listed
    for r in j.get('Resources', []) or []:
        if r.get('ResourceType') == 'Original' and r.get('Dimensions'):
            try:
                W, H = [int(x) for x in r['Dimensions']]
                if w and W and W != w and sx:
                    sx = sx * w / W
                w, h = W, H
            except Exception:
                pass
    res.update(w=w, h=h, px_arcsec=sx * 3600 if sx else None)
    if sx and w and h:
        res['fov_arcmin'] = (w * sx * 60, h * sx * 60)
    return res


def sep_arcmin(ra1, d1, ra2, d2):
    r = math.radians
    a = math.sin(r(d1)) * math.sin(r(d2)) + math.cos(r(d1)) * math.cos(r(d2)) * math.cos(r(ra1 - ra2))
    return math.degrees(math.acos(max(-1, min(1, a)))) * 60


CATDES = re.compile(r"\b(NGC|IC|M|Messier|Abell|ACO|SN|SNR|PSR|RCW|Sh2|W|Cas|Sgr|Arp|HCG|Mrk|3C|4C|PKS|MACS|SPT-CL|ACT-CL|RX|1RXS|CXOU|G|N|DEM|Westerlund|Trumpler|Tr|Hen|Abell|NGC/IC|Kes|CTB|MSH|HH|LDN|Sh|J)\s?-?[A-Z]?\d[\w+\-\.]*", re.I)
NAMES = re.compile(r"\b(Cygnus A|Centaurus A|Perseus Cluster|Coma Cluster|Virgo Cluster|Hydra A|Eta Car(?:inae)?|Tycho|Crab|Kepler|Vela|Puppis A|Orion|Carina|Eagle|Omega|Lagoon|Trifid|Rosette|Pinwheel|Whirlpool|Sombrero|Antennae|Cartwheel|Stephan's Quintet|Bullet Cluster|El Gordo|Pandora|Phoenix Cluster|Cat's Eye|Helix|Ring Nebula|Dumbbell|Owl|Eskimo|Butterfly|Pillars of Creation|Cassiopeia A|Andromeda|Galactic Center|Sagittarius A|30 Doradus|Tarantula|Pleiades|Westerlund 1|Medusa|Jellyfish|Hand of God|Pencil)\b", re.I)


def queries(title, aka):
    t = re.sub(r'^Chandra :: Photo Album :: ', '', title or '')
    t = re.sub(r' :: .*$', '', t).strip()
    qs = []
    for s in [t] + re.split(r',\s*', aka or ''):
        for m in list(CATDES.finditer(s)) + list(NAMES.finditer(s)):
            q = m.group(0).strip(' .,')
            if len(q) > 2 and q not in qs:
                qs.append(q)
    if t and t not in qs:
        qs.append(t)
    return qs[:3]


def best_match(site, ra, dec, fov_arcmin, title, aka, maxq=2):
    """find press images on a djangoplicity site that cover (ra,dec)."""
    cands = []
    seen = set()
    for q in queries(title, aka)[:maxq]:
        for iid in search(site, q):
            if iid in seen:
                continue
            seen.add(iid)
            inf = info(site, iid)
            if not inf or inf.get('ra') is None or not inf.get('fov_arcmin'):
                continue
            s = sep_arcmin(ra, dec, inf['ra'], inf['dec'])
            half = max(inf['fov_arcmin']) / 2
            if s > half:
                continue
            # rough coverage of the composite field
            cov = 1.0 if s + (fov_arcmin or 0) / 2 <= min(inf['fov_arcmin']) / 2 else 0.5
            inf['sep_arcmin'] = round(s, 2)
            inf['coverage'] = cov
            cands.append(inf)
    cands.sort(key=lambda x: (-x['coverage'], x['px_arcsec'] or 99))
    return cands
