import re, sys, json, html, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
S = sys.argv[1]
urls = [l.split('\t')[1] for l in open(f'{S}/gallery_items.tsv', encoding='utf-8').read().splitlines()]
os.makedirs(f'{S}/pages', exist_ok=True)
def get(u):
    slug = u.rstrip('/').split('/')[-1]
    p = f'{S}/pages/{slug}.html'
    if not os.path.exists(p):
        for i in range(4):
            try:
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (catalog-tool)'})
                d = urllib.request.urlopen(req, timeout=60).read()
                open(p, 'wb').write(d); break
            except Exception as e:
                time.sleep(3 * (i + 1))
        else:
            return {'url': u, 'error': True}
    t = open(p, encoding='utf-8', errors='replace').read()
    def m(rx):
        r = re.search(rx, t, re.S); return html.unescape(r.group(1)).strip() if r else None
    rec = {'url': u, 'slug': slug,
           'title': m(r'<meta property="og:title" content="([^"]*)"'),
           'published': m(r'datePublished":"([^"]*)"'),
           'desc': m(r'<meta property="og:description" content="([^"]*)"'),
           'cats': re.findall(r'href="/gallery/category/([^"/]+)', t),
           'colls': re.findall(r'href="/gallery/gallery-collection/([^"/]+)', t),
           'dl': []}
    for row in re.findall(r'<tr>(.*?)</tr>', t[t.find('vim-dl-cont'):], re.S):
        name = re.search(r'vim-dl-name">([^<]*)', row)
        res = re.search(r'vim-dl-res">([^<]*)', row)
        size = re.search(r'vim-dl-size">([^<]*)', row)
        href = re.search(r'href="([^"]+)"', row)
        if name and href:
            rec['dl'].append([name.group(1).strip(), res.group(1).strip() if res else '', size.group(1).strip() if size else '', href.group(1)])
    # credit
    rec['credit'] = m(r'(?:Credit|CREDIT)[^<]{0,5}</?[^>]*>\s*([^<]{3,300})')
    return rec
with ThreadPoolExecutor(4) as ex:
    out = list(ex.map(get, urls))
json.dump(out, open(f'{S}/gallery.json', 'w', encoding='utf-8'), indent=1)
print(len(out), sum(1 for r in out if r.get('error')))
