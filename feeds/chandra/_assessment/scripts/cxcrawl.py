import re, html, os, sys, json, hashlib, struct, urllib.request, urllib.error, time
from concurrent.futures import ThreadPoolExecutor
S=sys.argv[1] if len(sys.argv)>1 else '.'
CACHE=os.path.join(S,'web','cache'); os.makedirs(CACHE,exist_ok=True)
UA='Mozilla/5.0 (catalog research)'
BASE='https://chandra.harvard.edu'
def fetch(url, rng=None):
    key=hashlib.md5((url+'|'+str(rng)).encode()).hexdigest()
    p=os.path.join(CACHE,key)
    if os.path.exists(p):
        d=open(p,'rb').read()
        if d.startswith(b'__ERR__'): return None,{}
        meta=json.load(open(p+'.json')) if os.path.exists(p+'.json') else {}
        return d,meta
    h={'User-Agent':UA}
    if rng: h['Range']=rng
    for attempt in range(3):
        try:
            r=urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=60)
            d=r.read(); meta={'cr':r.headers.get('Content-Range'),'cl':r.headers.get('Content-Length'),'status':r.status,'url':r.geturl()}
            open(p,'wb').write(d); json.dump(meta,open(p+'.json','w')); return d,meta
        except urllib.error.HTTPError as e:
            if e.code in (404,403,410): open(p,'wb').write(b'__ERR__%d'%e.code); return None,{}
            time.sleep(2)
        except Exception as e:
            time.sleep(2)
    return None,{}
def text(h):
    h=re.sub(r'<script.*?</script>|<style.*?</style>|<!--.*?-->','',h,flags=re.S)
    return html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',h))).replace('\xa0',' ')
LABELS=['Credit','Release Date','Scale','Category','Coordinates \(J2000\)','Constellation','Observation Dates?','Observation Time','Obs\. ID','Instrument','Also Known As','References','Color Code','Distance Estimate','Distance','Rate this image','Visual Description','Image Use Policy']
def facts(txt):
    i=txt.find('Fast Facts'); t=txt[i:] if i>=0 else txt
    out={}
    pat=re.compile(r'(?<![A-Za-z])('+'|'.join(LABELS)+r')\s*[:\uFFFD]?\s')
    ms=list(pat.finditer(t))
    for k,m in enumerate(ms):
        lab=m.group(1).replace(chr(92),''); end=ms[k+1].start() if k+1<len(ms) else m.end()+600
        v=t[m.end():end].strip(' -\u2014:\ufffd>').strip()
        v=re.sub(r'(\s*-->)+','',v).strip()
        if lab not in out and v: out[lab]=v[:600]
    return out
def size_mb(s):
    m=re.search(r'([\d.]+)\s*(kb|mb|gb)',s or '',re.I)
    if not m: return None
    v=float(m.group(1)); u=m.group(2).lower()
    return v/1024 if u=='kb' else v*1024 if u=='gb' else v
def jpeg_dims(d):
    i=2
    while i+9<len(d):
        if d[i]!=0xFF: i+=1; continue
        mk=d[i+1]
        if mk in (0xD8,0x01) or 0xD0<=mk<=0xD7: i+=2; continue
        L=struct.unpack('>H',d[i+2:i+4])[0]
        if mk in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
            hh,ww=struct.unpack('>HH',d[i+5:i+9]); return ww,hh
        i+=2+L
    return None
def tiff_dims(url,d):
    if len(d)<8: return None
    bo='<' if d[:2]==b'II' else '>'
    if struct.unpack(bo+'H',d[2:4])[0]!=42: return None
    off=struct.unpack(bo+'I',d[4:8])[0]
    if off+2+12*40<=len(d): blk=d[off:]
    else:
        blk,_=fetch(url,'bytes=%d-%d'%(off,off+4095))
        if not blk: return None
    n=struct.unpack(bo+'H',blk[:2])[0]; w=h=None
    for k in range(min(n,200)):
        e=blk[2+12*k:14+12*k]
        if len(e)<12: break
        tag,typ,cnt=struct.unpack(bo+'HHI',e[:8])
        val=struct.unpack(bo+'H',e[8:10])[0] if typ==3 else struct.unpack(bo+'I',e[8:12])[0]
        if tag==256: w=val
        if tag==257: h=val
    return (w,h) if w and h else None
def xmp_info(d):
    if not d: return {}
    s=d.decode('latin-1')
    info={'avm': ('communicatingastronomy.org/avm' in s) or ('avm:' in s)}
    keys=sorted(set(re.findall(r'avm:(Spatial\.[A-Za-z]+)',s)))
    info['spatial']=keys
    def grab(k):
        m=re.search(r'avm:'+re.escape(k)+r'>\s*(?:<rdf:Seq>)?(.*?)</(?:rdf:Seq|avm:'+re.escape(k)+')',s,re.S)
        if not m:
            m=re.search(r'avm:'+re.escape(k)+r'="([^"]*)"',s)
        return re.sub(r'<[^>]+>',' ',m.group(1)).split() if m else None
    for k in ['Spatial.ReferenceValue','Spatial.ReferenceDimension','Spatial.ReferencePixel','Spatial.Scale','Spatial.Rotation','Spatial.CDMatrix','Spatial.Quality','Spatial.CoordsystemProjection']:
        v=grab(k)
        if v: info[k]=v
    info['wcs']=bool(info.get('Spatial.ReferenceValue') and (info.get('Spatial.Scale') or info.get('Spatial.CDMatrix')))
    return info
def probe(url, kind):
    """kind: tif|jpg; returns dict(dims, avm info, bytes)"""
    r={'url':url}
    if kind=='jpg':
        d,m=fetch(url,'bytes=0-2097151')
        if d is None: r['missing']=True; return r
        r['bytes']=int((m.get('cr') or '/0').split('/')[-1] or 0) if m.get('cr') else len(d)
        r['dims']=jpeg_dims(d); r.update(xmp_info(d)); return r
    d,m=fetch(url,'bytes=0-1048575')
    if d is None: r['missing']=True; return r
    tot=(m.get('cr') or '/').split('/')[-1]
    r['bytes']=int(tot) if tot.isdigit() else len(d)
    r['dims']=tiff_dims(url,d)
    xi=xmp_info(d)
    if not xi.get('avm') and r['bytes']>len(d):
        d2,_=fetch(url,'bytes=-2097152'); x2=xmp_info(d2)
        if x2.get('avm'): xi=x2
    r.update(xi); return r
def links(h):
    out=[]
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',h,re.S|re.I):
        out.append((m.group(1),text(m.group(2)).strip(),m.start()))
    return out
def parse_release(rel):
    """rel like 2026/kepler"""
    url=f'{BASE}/photo/{rel}/'
    d,_=fetch(url)
    if d is None: return {'rel':rel,'error':'page missing'}
    h=d.decode('utf-8','replace'); txt=text(h)
    R={'rel':rel,'url':url}
    m=re.search(r'<title>(.*?)</title>',h,re.S); R['title']=text(m.group(1)).strip() if m else ''
    m=re.search(r'<meta[^>]+og:title[^>]+content="([^"]*)"',h); 
    if m: R['title']=html.unescape(m.group(1))
    R['facts']=facts(txt)
    L=links(h); R['downloads']=[]
    for href,t,pos in L:
        if re.search(r'\.(tif|tiff|jpg|jpeg|png|fits|fits\.gz|zip|psb)$',href,re.I) and '/' not in href.strip('./') and not href.endswith('_thm.jpg'):
            R['downloads'].append((href,t))
    R['fits_links']=[x for x,_,_ in L if re.search(r'\.fits(\.gz)?$|fits\.zip$',x,re.I)]
    R['has_more']=any(x.endswith('more.html') for x,_,_ in L)
    R['more']=[]
    if R['has_more']:
        d2,_=fetch(url+'more.html')
        if d2:
            h2=d2.decode('utf-8','replace')
            R['fits_links'] += [x for x,_,_ in links(h2) if re.search(r'\.fits(\.gz)?$|fits\.zip$',x,re.I)]
            starts=[m.start() for m in re.finditer(r'<a\s[^>]*href="[^"/]+\.jpe?g"[^>]*>\s*<img[^>]+_thm\.jpe?g',h2,re.I)]
            blocks=[]
            for k,p in enumerate(starts):
                seg=h2[p: starts[k+1] if k+1<len(starts) else p+5000]
                tf=[x for x,t,_ in links(seg) if re.search(r'\.tiff?$',x,re.I)]
                jm=re.search(r'href="([^"]+\.jpe?g)"',seg,re.I); jp=jm.group(1) if jm else None
                st=text(seg)
                cm=re.search(r'Credit:?\s*(.*?)(?:\)\s*)?(?:Scale\b|$)',st)
                sm=re.search(r'Scale:?\s*(.{0,120})',st)
                blocks.append({'tif':tf[0] if tf else None,'jpg':jp,'credit':(cm.group(1) if cm else '')[:400].strip(' ()'),'scale':sm.group(1) if sm else '','ctx':st[:250]})
            R['more']=blocks
    return R
if __name__=='__main__':
    print(parse_release(sys.argv[2]))
