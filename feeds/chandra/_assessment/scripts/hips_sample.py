"""Sample a HiPS survey (PNG/JPEG tiles) onto a TAN grid, without hips2fits.

    sample(service_url, order, tile_width, ra, dec, fov_deg, npix, cache_dir, fmt='png', layout=...)
returns (rgb uint8 array [npix, npix, 3], astropy WCS in FITS convention, i.e. row 0 = bottom).

The within-tile layout is the HiPS standard's nested-pixel interleave; `layout` picks
which deinterleaved coordinate is the image column/row and whether they are flipped.
The default was checked against SkyView DSS2 FITS (see check_layout()).
"""
import os, io, hashlib, urllib.request
import numpy as np
from PIL import Image
from astropy.wcs import WCS
from astropy_healpix import HEALPix
import astropy.units as u

UA = {'User-Agent': 'wwt-core-catalogs chandra feed (registration)'}


def tan_wcs(ra, dec, fov_deg, npix):
    w = WCS(naxis=2)
    w.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [npix / 2 + 0.5, npix / 2 + 0.5]
    s = fov_deg / npix
    w.wcs.cdelt = [-s, s]
    return w


def _compress(v):
    # take every other bit of v (bits 0,2,4,...) and pack them
    v = v & 0x5555555555555555
    v = (v | (v >> 1)) & 0x3333333333333333
    v = (v | (v >> 2)) & 0x0F0F0F0F0F0F0F0F
    v = (v | (v >> 4)) & 0x00FF00FF00FF00FF
    v = (v | (v >> 8)) & 0x0000FFFF0000FFFF
    v = (v | (v >> 16)) & 0x00000000FFFFFFFF
    return v


def _tile(service, order, ipix, cache_dir, fmt):
    d = (ipix // 10000) * 10000
    url = f'{service}/Norder{order}/Dir{d}/Npix{ipix}.{fmt}'
    p = os.path.join(cache_dir, hashlib.md5(url.encode()).hexdigest() + '.' + fmt)
    if not os.path.exists(p):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception:
            data = b''
        open(p, 'wb').write(data)
    data = open(p, 'rb').read()
    if not data:
        return None
    return np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))


def sample(service, order, tw, ra, dec, fov_deg, npix, cache_dir, fmt='png', layout=(1, 0, False, False)):
    os.makedirs(cache_dir, exist_ok=True)
    w = tan_wcs(ra, dec, fov_deg, npix)
    yy, xx = np.mgrid[0:npix, 0:npix]
    sky = w.pixel_to_world(xx.ravel(), yy.ravel())
    k = int(np.log2(tw))
    hp = HEALPix(nside=2 ** (order + k), order='nested')
    idx = hp.lonlat_to_healpix(sky.ra, sky.dec).astype(np.int64)
    tile = idx >> (2 * k)
    sub = idx & ((1 << (2 * k)) - 1)
    a = _compress(sub)
    b = _compress(sub >> 1)
    c = [a, b][layout[0]]
    r = [a, b][layout[1]]
    if layout[2]:
        r = tw - 1 - r
    if layout[3]:
        c = tw - 1 - c
    out = np.zeros((npix * npix, 3), np.uint8)
    for t in np.unique(tile):
        im = _tile(service, order, int(t), cache_dir, fmt)
        if im is None:
            continue
        m = tile == t
        out[m] = im[r[m], c[m]]
    # row 0 of `out` is FITS y=0 (bottom); flip to image (top-down) order for callers
    return out.reshape(npix, npix, 3)[::-1], w


def check_layout(cache_dir):
    """Find the tile layout by correlating DSS2-red HiPS samples with SkyView's DSS2 Red FITS."""
    from astroquery.skyview import SkyView
    ra, dec, fov, n = 83.6331, 22.0145, 0.15, 300
    ref = SkyView.get_images(position=f'{ra},{dec}', survey='DSS2 Red', pixels=n, width=fov * u.deg, height=fov * u.deg,
                             projection='Tan', coordinates='J2000')[0][0]
    rw = WCS(ref.header)
    rd = ref.data.astype(float)[::-1]  # top-down
    best = None
    for lay in [(i, 1 - i, f1, f2) for i in (0, 1) for f1 in (False, True) for f2 in (False, True)]:
        img, w = sample('https://irsa.ipac.caltech.edu/data/hips/CDS/DSS2/red', 9, 512, ra, dec, fov, n, cache_dir, 'jpg', lay)
        g = img.mean(axis=2)
        cc = np.corrcoef(g.ravel(), rd.ravel())[0, 1]
        print(lay, round(cc, 3))
        if best is None or cc > best[0]:
            best = (cc, lay)
    return best


if __name__ == '__main__':
    import sys
    print(check_layout(sys.argv[1]))
