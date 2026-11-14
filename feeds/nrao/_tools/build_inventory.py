import json, sys, os
W, OUT = sys.argv[1], sys.argv[2]
rel = json.load(open(f'{W}/dl/releases.json', encoding='utf-8'))
gal = json.load(open(f'{W}/dl/gallery.json', encoding='utf-8'))
probe = {}
for f in ('probe_out_rel.json', 'probe_out_gallery.json'):
    for r in json.load(open(f'{W}/dl/{f}', encoding='utf-8')):
        if r.get('avm') or r['img'] not in probe:
            probe[r['img']] = r
U = 'https://public.nrao.edu/wp-content/uploads/'


def where(path):
    url = U + path
    hits = []
    for r in rel:
        if url in r.get('imgs', []) and (r.get('published') or '') >= '2019-06':
            hits.append((r['published'][:10], r['url']))
    for g in gal:
        if any(d[3] == url for d in g['dl']) and (g.get('published') or '') >= '2019-06':
            hits.append((g['published'][:10], g['url']))
    hits.sort()
    return hits[0] if hits else ('', '')


def size(path):
    fn = f"{W}/thumbs/{path.replace('/', '_')}.thumb.jpg.size"
    return open(fn).read() if os.path.exists(fn) else ''


READY = [  # full, self-consistent AVM (ReferenceDimension matches the pixels)
    dict(id='nrao20-double-boomerang', path='2020/05/Xgalaxy_composite_02042020_SD.jpg',
         name='PKS 2014-55 "Double Boomerang" radio galaxy (MeerKAT + DES)', band='Multi', xbands='Visible,Radio',
         near='none in catalogue',
         note="SIN projection, no CoordinateFrame tag (assume ICRS); 5861 px, 0.26\"/px, 25.7' FOV"),
    dict(id='nrao20-cena-radio', path='2020/02/CenA_Radio_Red.jpg', name='Centaurus A inner lobes (VLA)',
         band='Radio', xbands='',
         near='eso0005b (radio+optical composite), eso1222c (APEX), Chandra composites: different data, keep',
         note="2400 px, 0.34\"/px, 13.4' FOV"),
    dict(id='nrao20-m81-hi', path='2020/02/m81_radio_only_GBTandVLA.tif',
         name='M81 group in neutral hydrogen (GBT + VLA)', band='Radio', xbands='',
         near='no radio imageset within 0.5 deg',
         note='only 720 px (15"/px), but a 3 deg HI map; PinpointWCS solution'),
    dict(id='nrao21df05b', path='2022/06/nrao21df05b.jpg', name='Host galaxy of FRB 20190520B (VLA + optical)',
         band='Multi', xbands='Visible,Radio', near='none in catalogue',
         note='1920x1080, 0.03"/px, 57" FOV; PinpointWCS solution'),
    dict(id='nrao-antennae-alma-hst', path='2018/03/AntennaeZoomAllRGB.jpg', name='Antennae galaxies (ALMA + Hubble)',
         band='Multi', xbands='Visible,Radio',
         near='NEAR eso1137a (ALMA+HST composite, 3375 px at 0.052"/px). This one is 4005 px at 0.051"/px: '
              'same density, ~19% wider field. User decides keep/replace.',
         note='file uploaded 2018, reused in the 2023 "ALMA at 10" release'),
]

# (path, object, band, partial AVM, anchor, note)
MANUAL = [
    ('2019/06/nrao19cb05_SagA_FITs_composite.png', 'Sgr A* cool gas ring (ALMA)', 'Radio', '',
     'Sgr A* VLBI position + scale from Murchikova et al. 2019; nothing to match in surveys', 'tiny field (~2")'),
    ('2019/09/Radio_blue_2MB.jpg', 'Galactic Centre radio bubbles (MeerKAT)', 'Radio', '',
     'Better: tile the public SARAO MeerKAT Galactic Centre mosaic FITS (Heywood et al. 2019/2022) instead of this 1575 px JPEG; else compact sources vs. "Galactic Center 90cm" in catalogue', ''),
    ('2019/11/finalN4631v6-fieldReversals-scaled.jpg', 'NGC 4631 magnetic ropes (VLA CHANG-ES + optical)', 'Multi', '',
     'Field stars in the optical layer vs. DSS2 / SDSS', ''),
    ('2019/12/nrao19in01a.jpg', 'MAMBO-9 (ALMA + HST)', 'Multi', '',
     'HST COSMOS galaxies in frame', 'tiny field'),
    ('2019/12/nrao20ir01_ALMAComposite.jpg', 'NGC 6240 (ALMA + HST)', 'Multi', '',
     'Hubble NGC 6240 / PanSTARRS (nuclei + stars)', ''),
    ('2020/04/nrao20in04_ALMAContOCIIPcomposite.jpg', 'Wolfe Disk DLA0817g (ALMA + HST)', 'Multi', 'PARTIAL: CRVAL/CRPIX, no scale',
     'Scale + rotation from HST galaxies in frame', 'tiny field'),
    ('2020/06/nrao20in08_Mosaic_ALMA_HST_comp_purple_05192020.jpg', 'Giant young cluster forming (ALMA + HST mosaic)', 'Multi', 'PARTIAL: CRVAL/CRPIX, no scale',
     'Stars vs. Gaia DR3 / HST: only scale + rotation missing', ''),
    ('2020/07/nrao20in12_RULup_blue.jpg', 'RU Lup disk spiral (ALMA)', 'Radio', 'PARTIAL: CRVAL/CRPIX, no scale',
     'DSHARP / Huang et al. 2020 public FITS; star at Gaia position', 'tiny field'),
    ('2020/07/N4217b.jpeg', 'NGC 4217 magnetic field (VLA + SDSS)', 'Multi', '',
     'SDSS / DSS2 field stars (an "Original TIFF" exists, also without AVM)', ''),
    ('2020/08/nrao20df_AGNImage_Composite.jpg', 'Young stop-and-start radio jets', 'Multi', '',
     'Object ID + scale from the paper (Nyland et al. 2020); then optical counterpart in PanSTARRS', 'needs object ID'),
    ('2020/11/IC310_composite_cropped.jpg', 'IC 310, Perseus cluster (VLA + optical)', 'Multi', '',
     'Field stars vs. PanSTARRS / SDSS', ''),
    ('2020/11/NGC1265_composite_cropped.jpg', 'NGC 1265, Perseus cluster (VLA + optical)', 'Multi', '',
     'Field stars vs. PanSTARRS / SDSS', ''),
    ('2020/11/NGC1275_composite_cropped.jpg', 'NGC 1275 / Perseus A (VLA + optical)', 'Multi', '',
     'Field stars vs. PanSTARRS / SDSS', ''),
    ('2021/03/nrao21df_HSTVLA_Composite.jpg', 'Lensed faint radio galaxy behind MACS J0717.5+3745 (HST + VLA)', 'Multi', '',
     'Hubble Frontier Fields MACS J0717 (cluster galaxies)', '10350 px'),
    ('2021/04/W51e2_cont_bluered_composite_cropped.jpg', 'W51 e2 protostellar outflows (ALMA)', 'Radio', '',
     'ALMA archive FITS (Goddi et al. 2020); no stars in frame', 'tiny field'),
    ('2021/04/W51e8_cont_redblue_composite_cropped.jpg', 'W51 e8 protostellar outflows (ALMA)', 'Radio', '',
     'ALMA archive FITS (Goddi et al. 2020)', 'tiny field'),
    ('2021/04/W51n_cont_bluered_composite_cropped.jpg', 'W51 North protostellar outflows (ALMA)', 'Radio', '',
     'ALMA archive FITS (Goddi et al. 2020)', 'tiny field'),
    ('2021/05/nrao21df_w49a-zoomout.jpg', 'W49A star-forming region (VLA + IR)', 'Multi', '',
     'Stars vs. 2MASS / Spitzer GLIMPSE', ''),
    ('2021/06/sPHANGS_ngc628_composite_color-copy.jpg', 'PHANGS-ALMA NGC 628 (ALMA + optical)', 'Multi', '',
     'Stars vs. DSS2 / PanSTARRS, or PHANGS-ALMA public moment-0 FITS',
     'NEAR NRAO_Gallery_nrao18cb12d (2019 PHANGS NGC 628 composite, already in catalogue)'),
    ('2021/06/PHANGS_ngc4254w_composite_color.jpg', 'PHANGS-ALMA NGC 4254 (M99)', 'Multi', '',
     'DSS2 / SDSS stars, or PHANGS-ALMA FITS', ''),
    ('2021/06/PHANGES_ngc4321_composite_color.jpg', 'PHANGS-ALMA NGC 4321 (M100)', 'Multi', '',
     'DSS2 / SDSS stars, or PHANGS-ALMA FITS', ''),
    ('2021/06/sPHANGS_ngc1385_COMPOSITE_color.jpg', 'PHANGS-ALMA NGC 1385', 'Multi', '',
     'DSS2 / PanSTARRS stars, or PHANGS-ALMA FITS', ''),
    ('2021/06/sPHANGS_ngc1566_Composite_color.jpg', 'PHANGS-ALMA NGC 1566', 'Multi', '',
     'DSS2 stars, or PHANGS-ALMA FITS', ''),
    ('2021/06/sPHANGS_ngc3351_composite_color.jpg', 'PHANGS-ALMA NGC 3351 (M95)', 'Multi', '',
     'DSS2 / SDSS stars, or PHANGS-ALMA FITS', ''),
    ('2021/06/sPHANGS_ngc3627_Composite_color.jpg', 'PHANGS-ALMA NGC 3627 (M66)', 'Multi', '',
     'DSS2 / SDSS stars, or PHANGS-ALMA FITS', ''),
    ('2021/06/PHANGS_NGC4535_composite_color.jpg', 'PHANGS-ALMA NGC 4535', 'Multi', '',
     'DSS2 / SDSS stars, or PHANGS-ALMA FITS', ''),
    ('2021/06/sPHANGS_NGC5248_composite_color.jpg', 'PHANGS-ALMA NGC 5248', 'Multi', '',
     'DSS2 / SDSS stars, or PHANGS-ALMA FITS', ''),
    ('2021/06/nrao21ao03a.jpg', 'Elias 2-27 spiral disk (ALMA)', 'Radio', 'PARTIAL: SIN + CRVAL, no scale',
     'DSHARP public FITS; star at Gaia position', 'tiny field'),
    ('2021/07/nrao20df_GLOSTAR.jpg', 'GLOSTAR Galactic-plane strip (VLA)', 'Radio', '',
     'GLOSTAR public FITS, or compact HII regions vs. Spitzer GLIMPSE / WISE', '12500 px'),
    ('2021/07/NGC4921_HubbleALMA.jpeg', 'NGC 4921 ram-pressure stripping (HST + ALMA)', 'Multi', '',
     'Hubble / SDSS stars and background galaxies', ''),
    ('2021/09/Fig6_HD163296_HCN_260GH_hf1_BLUElog_black_3K75percent.jpg', 'HD 163296 in HCN (ALMA MAPS)', 'Radio', '',
     'MAPS public FITS (Oberg et al. 2021); star at Gaia position', 'tiny field; eso1818a (continuum) in catalogue'),
    ('2021/10/NGC4567_4568_compositeHST_v2.jpg', 'VERTICO NGC 4567/4568 (ALMA + HST)', 'Multi', '',
     'SDSS / Hubble stars, or VERTICO public FITS', ''),
    ('2021/10/ngc4254_composite_HST.png', 'VERTICO NGC 4254 (ALMA + HST)', 'Multi', '',
     'SDSS / Hubble stars, or VERTICO public FITS', 'NEAR PHANGS NGC 4254 above'),
    ('2021/10/IC1613.png', 'IC 1613 neutral hydrogen (VLA)', 'Radio', '',
     'No stars: needs the HI FITS (LITTLE THINGS / paper data)', ''),
    ('2021/12/nrao21df04_M87_Total_Intensity_MagRot_112021.jpeg', 'M87 jet double helix (VLA)', 'Radio', '',
     'Jet knots vs. Hubble / Chandra M87 imagery in catalogue', ''),
    ('2022/04/0379_cropped.jpeg', 'Post-starburst galaxy 0379 (HST + ALMA)', 'Multi', '',
     'SDSS ID from Smercina et al. 2022, then SDSS / PanSTARRS stars', 'needs object ID'),
    ('2022/04/0570_cropped.jpeg', 'Post-starburst galaxy 0570 (HST + ALMA)', 'Multi', '',
     'SDSS ID from Smercina et al. 2022, then SDSS / PanSTARRS stars', 'needs object ID'),
    ('2022/05/nrao22ao08_b.jpg', 'A1689-zD1 behind Abell 1689 (ALMA + HST)', 'Multi', 'PARTIAL: mixed CRVALs, CRPIX of a component',
     'Hubble Abell 1689 (in catalogue): cluster galaxies', ''),
    ('2022/06/nrao22ao09_MacGregor_HD51343_HST_ALMA.jpg', 'HD 53143 debris disk (HST + ALMA)', 'Multi', 'PARTIAL: CRVAL/CRPIX, no scale',
     'Star at Gaia position + scale from the paper', 'tiny field'),
    ('2022/06/nrao22ao01_Wong_Molecualrcloud_HSTALMA_composite.jpg', '30 Doradus molecular filaments (HST + ALMA)', 'Multi', 'PARTIAL: CRVAL/CRPIX, no scale',
     'Stars vs. Hubble 30 Dor (in catalogue) / Gaia', ''),
    ('2022/08/SDSS_J14481010_CO21_Composite.png', 'SDSS J1448+1010 merger tidal tails (ALMA + optical)', 'Multi', '',
     'SDSS / PanSTARRS galaxies in frame', ''),
    ('2023/02/Apr299.jpeg', 'Arp 299 (2023 release image)', 'Multi', '',
     'Hubble Arp 299 / PanSTARRS', 'probably duplicates NRAO_Gallery010 "Arp 299" (2019 feed): compare first'),
    ('2025/03/spt2349_extended_molecular_gas_full_nsulzenauer.jpg', 'SPT2349-56 protocluster molecular gas (ALMA + optical/IR)', 'Multi', '',
     'Galaxies vs. HST/JWST archive', 'confirm it is data, not an artist composite'),
    ('2026/06/sgra_co_xray.jpg', 'Sgr A* surroundings in CO + X-ray', 'Multi', '',
     'Chandra Galactic Centre imagery in catalogue (Sgr A East shell)', ''),
    ('2026/07/EON_HIandWISEbare.png', 'Orion Nebula hidden HI shell (VLA + WISE)', 'Multi', '',
     'WISE All-Sky in WWT (stars + nebula)', 'the easiest of the batch'),
]

data = {'ready': [], 'manual': []}
for r in READY:
    url = U + r.pop('path')
    p = probe.get(url, {})
    d, page = where(url[len(U):])
    r.update(url=url, release=page, date=d, avm=p.get('avm'))
    data['ready'].append(r)
for path, obj, band, partial, anchor, note in MANUAL:
    d, page = where(path)
    data['manual'].append(dict(url=U + path, object=obj, band=band, avm=partial or 'none', size=size(path),
                               date=d, release=page, anchor=anchor, note=note))
json.dump(data, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(data['ready']), len(data['manual']), sum(1 for m in data['manual'] if m['avm'] != 'none'))
for m in data['ready'] + data['manual']:
    if not m['date']:
        print('NO DATE', m['url'])
