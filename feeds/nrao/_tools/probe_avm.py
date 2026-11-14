"""For each candidate (json list with 'img' url), range-fetch head+tail and parse AVM Spatial tags."""
import sys, json, re, urllib.request, os
from concurrent.futures import ThreadPoolExecutor
inp, outp = sys.argv[1], sys.argv[2]
cands = json.load(open(inp, encoding='utf-8'))
def rng(u, spec):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (catalog-tool)', 'Range': spec})
    r = urllib.request.urlopen(req, timeout=120)
    return r.read(), r.headers.get('Content-Range'), r.headers.get('Content-Length')
def parse(x):
    out = {}
    for tag in ['CoordinateFrame','Equinox','CoordsystemProjection','Quality','Rotation','Notes']:
        m = re.search(rf'avm:Spatial\.{tag}(?:="([^"]*)"|>\s*(?:<rdf:Alt>\s*<rdf:li[^>]*>)?([^<]*))', x)
        if m: out[tag] = (m.group(1) or m.group(2) or '').strip()
    for tag in ['ReferenceValue','ReferenceDimension','ReferencePixel','Scale','CDMatrix']:
        m = re.search(rf'<avm:Spatial\.{tag}>(.*?)</avm:Spatial\.{tag}>', x, re.S)
        if m: out[tag] = re.findall(r'<rdf:li>([^<]*)</rdf:li>', m.group(1))
    return out
def probe(c):
    u = c['img']; res = dict(c)
    try:
        head, cr, cl = rng(u, 'bytes=0-4000000')
        total = int(cr.split('/')[-1]) if cr and '/' in cr else len(head)
        blob = head
        if total > len(head):
            tail, _, _ = rng(u, f'bytes={max(len(head), total-4000000)}-')
            blob += tail
        res['bytes'] = total
        i = blob.find(b'<x:xmpmeta')
        if i < 0:
            res['avm'] = None
        else:
            x = blob[i:blob.find(b'</x:xmpmeta>', i) + 12].decode('utf-8', 'replace')
            res['avm'] = parse(x)
    except Exception as e:
        res['err'] = repr(e)
    return res
with ThreadPoolExecutor(4) as ex:
    out = list(ex.map(probe, cands))
json.dump(out, open(outp, 'w', encoding='utf-8'), indent=1)
print(len(out))
