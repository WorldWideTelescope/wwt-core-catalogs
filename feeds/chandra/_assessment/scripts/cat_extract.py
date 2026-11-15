import xml.etree.ElementTree as ET, glob, json, re, sys
out=[]; allsets=[]
for f in glob.glob('imagesets/sky__*.xml'):
    root=ET.parse(f).getroot()
    for el in root.iter('ImageSet'):
        a=dict(el.attrib)
        for c in el: a[c.tag]=(c.text or '').strip()
        a['_file']=f
        allsets.append(a)
        cu=a.get('CreditsUrl','')
        ap=a.get('Xastropix_ids','')
        if 'chandra.harvard.edu/photo' in cu or ap.lower().startswith('chandra') or 'chandra|' in ap.lower():
            out.append(a)
print(len(out), len(allsets))
json.dump(out,open(sys.argv[1]+'/catalog_chandra.json','w'),indent=1)
json.dump(allsets,open(sys.argv[1]+'/catalog_all.json','w'))
from collections import Counter
print(Counter(a['_file'] for a in out)); print(Counter(a.get('Xbands') for a in out).most_common(15))
print(Counter(bool(re.search(r'chandra.harvard.edu/photo/\d{4}/',a.get('CreditsUrl',''))) for a in out))
print(Counter(a.get('Projection') for a in out), Counter(a['Url'].split('/')[2] for a in out).most_common(8))
