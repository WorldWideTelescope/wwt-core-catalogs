import re

BAND_RE = re.compile(
    r'(?<![A-Za-z])('
    r'X-?rays?(?:/Radio)?|Optical(?:/IR|/Infrared)?|Visible|Infra-?red|Near[- ]?IR|Near[- ]?Infrared|Mid[- ]?IR|Mid[- ]?Infrared|Far[- ]?IR|'
    r'IR|Radio|Ultraviolet|UV|H-?alpha|Hα|Gamma[- ]?rays?|Gamma|Millimeter|Sub-?millimeter|Sub-?mm|mm|Microwave|'
    r'Image [Pp]rocessing|Processing|Illustration|Illustrations|Spectr(?:um|a)|Lensing [Mm]ap|Mass [Mm]ap|Hydrogen|Polari[sz]ation|IXPE|'
    r'Left|Right|Inset|Top|Bottom|Panel|Composite'
    r')\s*(?:\(|:|-\s)'
)

BAND_NORM = [
    (r'^x', 'XRay'), (r'^(optical|visible)', 'Visible'), (r'^(infra|near|mid|far|ir)', 'IR'), (r'^radio', 'Radio'),
    (r'^(ultra|uv)', 'Ultraviolet'), (r'^h', 'HydrogenAlpha'), (r'^gamma', 'Gamma'), (r'^(milli|sub|mm|micro)', 'Microwave'),
    (r'^(image|process|illus|left|right|inset|top|bottom|panel|composite|spectr|lensing|mass|polar)', None), (r'^ixpe', 'XRay'),
]

MISSIONS = [
    ('Chandra', r'CXC|CXO|Chandra'),
    ('JWST', r'JWST|Webb|ESA/CSA|NASA/ESA/CSA|CSA/'),
    ('Hubble', r'STScI|STScl|HST|Hubble|ESA/Hubble|Hubble Heritage|NASA/ESA(?!/CSA)|ESA/NASA'),
    ('WISE', r'WISE|UCLA'),
    ('2MASS', r'2MASS|UMass'),
    ('Spitzer', r'Spitzer|SSC|SST|JPL'),
    ('Herschel', r'Herschel|PACS|SPIRE|HOBYS'),
    ('Planck', r'Planck'),
    ('Euclid', r'Euclid'),
    ('ALMA', r'ALMA'),
    ('APEX', r'APEX'),
    ('ESO', r'ESO|VLT|VISTA|VST|MPG'),
    ('VLA/NRAO', r'NRAO|VLA|AUI|GBT|VLBA|Jansky'),
    ('MeerKAT', r'MeerKAT|SARAO|SKA'),
    ('ASKAP/ATCA', r'CSIRO|ASKAP|ATCA|ATNF|Parkes|EMU|RACS'),
    ('LOFAR', r'LOFAR|ASTRON'),
    ('GMRT', r'GMRT|NCRA|TIFR'),
    ('MWA', r'MWA|Murchison|GLEAM'),
    ('Effelsberg', r'Effelsberg|MPIfR'),
    ('JCMT', r'JCMT|SCUBA|EAO'),
    ('Gemini', r'Gemini'),
    ('NOIRLab', r'NOIRLab|NOAO|CTIO|KPNO|Kitt Peak|WIYN|DECam|DES\b|Blanco|Mayall|SOAR|Legacy Survey|DESI|DECaLS|NSF|AURA'),
    ('Subaru', r'Subaru|NAOJ|HSC'),
    ('CFHT', r'CFHT|Canada-France'),
    ('Pan-STARRS', r'Pan-?STARRS|PS1'),
    ('SDSS', r'SDSS|Sloan'),
    ('DSS', r'DSS|Digiti[sz]ed Sky|POSS|Palomar'),
    ('UKIRT', r'UKIRT|UKIDSS|WFCAM'),
    ('INT/WHT/ING', r'Isaac Newton|INT\b|WHT|ING\b|IPHAS'),
    ('GALEX', r'GALEX'),
    ('Swift', r'Swift'),
    ('XMM-Newton', r'XMM'),
    ('eROSITA', r'eROSITA|eRASS'),
    ('IXPE', r'IXPE|MSFC'),
    ('NuSTAR', r'NuSTAR'),
    ('Fermi', r'Fermi'),
    ('SOFIA', r'SOFIA'),
    ('ROSAT', r'ROSAT'),
    ('Kepler/TESS', r'Kepler|TESS'),
    ('MSX', r'MSX'),
    ('IRAS', r'IRAS'),
    ('Keck/LBT/MMT', r'Keck|LBT|MMT|Magellan')
    ,('SMA', r'SMA|ASIAA')
    ,('EHT/VLBI', r'EHT|EVN|VLBI'),
    ('SDO/Solar', r'SDO|SOHO'),
    ('Amateur', r'Gendler|Block|Mount Lemmon|SkyCenter|Kitt Peak|Wildfire|Lorand|Fox|Seiden|Croman|Pugh|Hanson|Dyer|DeepSkyColors|Astrophotograph|Davide|Pinter|Kerr|Rolf|Carlos|Murray|Morrison'),
]

# generic availability of a full-resolution, publicly downloadable version per mission
AVAIL = {
    'Hubble': ('yes', 'ESA/Hubble or STScI press TIFF (AVM); otherwise MAST HAP/HLA drizzled FITS (WCS, 0.04-0.1"/px)'),
    'JWST': ('yes', 'ESA/Webb or STScI press TIFF (AVM); otherwise MAST i2d FITS (WCS)'),
    'Spitzer': ('yes', 'IRSA SEIP/SHA mosaics FITS (WCS, 0.6"/px); Spitzer press TIFFs (AVM) for flagship targets'),
    'WISE': ('yes', 'IRSA AllWISE/unWISE FITS (WCS, 1.4-2.75"/px)'),
    'Herschel': ('yes', 'ESA HSA level-2.5/3 maps FITS (WCS)'),
    'Planck': ('yes', 'PLA HEALPix maps (coarse)'),
    'Euclid': ('yes', 'ESA Euclid press TIFF (AVM) / Q1-DR1 FITS'),
    'ALMA': ('yes', 'ALMA archive FITS (WCS)'),
    'APEX': ('partial', 'ESO archive FITS / ESO press image'),
    'ESO': ('yes', 'ESO press TIFF (AVM) or ESO archive Phase-3 FITS'),
    'VLA/NRAO': ('partial', 'NRAO archive / VLASS cutouts FITS; press PNGs rarely carry WCS'),
    'MeerKAT': ('partial', 'SARAO survey FITS (e.g. MeerKAT GC mosaic, SMGPS)'),
    'ASKAP/ATCA': ('partial', 'CASDA survey FITS (RACS/EMU), ATCA archive'),
    'LOFAR': ('partial', 'LoTSS DR2 FITS cutouts'),
    'GMRT': ('partial', 'TGSS/GMRT archive FITS'),
    'MWA': ('partial', 'GLEAM FITS'),
    'Effelsberg': ('partial', 'MPIfR survey FITS'),
    'JCMT': ('partial', 'CADC JCMT FITS'),
    'Gemini': ('yes', 'NOIRLab/Gemini press TIFF (AVM) or Gemini archive FITS'),
    'NOIRLab': ('yes', 'NOIRLab press TIFF (AVM) or Legacy Survey / Astro Data Archive FITS'),
    'Subaru': ('partial', 'HSC-SSP PDR FITS where covered; press images seldom tagged'),
    'CFHT': ('partial', 'CADC MegaPipe FITS'),
    'Pan-STARRS': ('yes', 'PS1 image cutout service FITS (WCS, 0.25"/px, <=6000 px per cutout)'),
    'SDSS': ('yes', 'SDSS SAS frames FITS (WCS, 0.396"/px)'),
    'DSS': ('yes', 'STScI DSS FITS (1.0-1.7"/px) - coarse; Pan-STARRS/Legacy Survey is the real upgrade'),
    '2MASS': ('yes', 'IRSA 2MASS atlas FITS (1"/px)'),
    'UKIRT': ('yes', 'WSA UKIDSS FITS'),
    'INT/WHT/ING': ('partial', 'IPHAS FITS'),
    'GALEX': ('yes', 'MAST GALEX FITS (1.5"/px)'),
    'Swift': ('yes', 'HEASARC FITS (coarser than Chandra)'),
    'XMM-Newton': ('yes', 'XMM archive FITS (coarser than Chandra)'),
    'eROSITA': ('yes', 'eRASS1 DR FITS (coarse)'),
    'IXPE': ('yes', 'HEASARC FITS (coarse)'),
    'NuSTAR': ('yes', 'HEASARC FITS (coarse)'),
    'Fermi': ('yes', 'FSSC (very coarse)'),
    'SOFIA': ('yes', 'IRSA SOFIA FITS'),
    'ROSAT': ('yes', 'HEASARC FITS (coarse)'),
    'MSX': ('yes', 'IRSA FITS'),
    'IRAS': ('yes', 'IRSA IRIS FITS'),
    'Kepler/TESS': ('partial', 'MAST'),
    'Keck/LBT/MMT': ('partial', 'KOA/observatory archives (FITS)'),
    'SMA': ('partial', 'SMA archive FITS'),
    'EHT/VLBI': ('n/a', 'inset only'),
    'SDO/Solar': ('n/a', ''),
    'Amateur': ('no', 'amateur/third-party image; ask the photographer'),
    'Other': ('unknown', ''),
}


def band_norm(lab):
    l = lab.lower()
    for pat, b in BAND_NORM:
        if re.match(pat, l):
            return b
    return None


def mission_of(src, band=None):
    for name, pat in MISSIONS:
        if re.search(pat, src):
            return name
    return 'Other'


def parse_credit(credit):
    """returns list of (band, source_text, mission)"""
    c = (credit or '').replace('’', "'").strip()
    c = re.sub(r'^\(?Credits?:?\s*', '', c)
    ms = list(BAND_RE.finditer(c))
    layers = []
    if not ms:
        # unlabelled credits on the Chandra album are Chandra-only images
        return [('XRay', c.strip(' ;,.()'), 'Chandra')]
    for k, m in enumerate(ms):
        end = ms[k + 1].start() if k + 1 < len(ms) else len(c)
        src = c[m.end():end].strip(' ;,.()&')
        b = band_norm(m.group(1))
        if b is None:
            continue
        if m.group(1).lower() == 'ixpe':
            layers.append(('XRay', 'IXPE ' + src, 'IXPE'))
            continue
        if not src:
            continue
        if m.group(1).lower().startswith('x-ray/radio') or m.group(1).lower().startswith('xray/radio'):
            layers.append(('XRay', src, mission_of(src)))
            layers.append(('Radio', src, mission_of(src)))
            continue
        # a single source text may hold several facilities (e.g. "NASA/STScI & ESO")
        parts = re.split(r'\s*(?:;|&| and |, (?=[A-Z][A-Za-z\-]+/))\s*', src)
        mm = []
        for p in parts:
            mi = mission_of(p)
            if mi not in mm:
                mm.append(mi)
        if len(mm) > 1 and 'Other' in mm:
            mm.remove('Other')
        if b == 'XRay':
            xm = [x for x in ('XMM-Newton', 'eROSITA', 'IXPE', 'NuSTAR', 'ROSAT', 'Swift') if re.search(dict(MISSIONS)[x], src)]
            mm = (['Chandra'] if re.search(r'CXC|CXO|Chandra', src) or not xm else []) + xm
        for mi in mm:
            layers.append((b, src, mi))
    if not layers:
        m0 = mission_of(c)
        layers = [('XRay' if m0 == 'Chandra' else None, c, m0)]
    return layers
