import re, sys, json, html, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
S = sys.argv[1]
t = open(f'{S}/release-sitemap.xml', encoding='utf-8').read()
urls = re.findall(r'<loc>([^<]*)</loc>', t)
os.makedirs(f'{S}/rpages', exist_ok=True)
def get(u):
    slug = u.rstrip('/').split('/')[-1] or 'news'
    p = f'{S}/rpages/{slug}.html'
    if not os.path.exists(p):
        for i in range(4):
            try:
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (catalog-tool)'})
                open(p, 'wb').write(urllib.request.urlopen(req, timeout=60).read()); break
            except Exception:
                time.sleep(3 * (i + 1))
        else:
            return {'url': u, 'error': True}
    t = open(p, encoding='utf-8', errors='replace').read()
    def m(rx):
        r = re.search(rx, t, re.S); return html.unescape(r.group(1)).strip() if r else None
    body = t
    imgs = sorted(set(re.findall(r'https://public\.nrao\.edu/wp-content/uploads/[^"\'\s)]+?\.(?:jpe?g|png|tiff?|fits)', body, re.I)))
    imgs = [i for i in imgs if not re.search(r'-\d+x\d+\.\w+$', i)]
    caps = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'<figcaption[^>]*>(.*?)</figcaption>', body, re.S)]
    if not caps:
        caps = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'wp-caption-text[^>]*>(.*?)</p>', body, re.S)]
    return {'url': u, 'slug': slug, 'title': m(r'<meta property="og:title" content="([^"]*)"'),
            'published': m(r'datePublished":"([^"]*)"'), 'imgs': imgs, 'caps': caps,
            'gallery': sorted(set(re.findall(r'https://public\.nrao\.edu/gallery/[^"\'#?]+', body)))}
with ThreadPoolExecutor(4) as ex:
    out = list(ex.map(get, urls))
json.dump(out, open(f'{S}/releases.json', 'w', encoding='utf-8'), indent=1)
print(len(out), sum(1 for r in out if r.get('error')))
