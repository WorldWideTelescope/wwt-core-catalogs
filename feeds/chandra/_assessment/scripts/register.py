"""Register fetched Chandra images that lack AVM WCS and write sidecar WCS files.

usage (base anaconda python, needs cv2 + astropy + astropy_healpix + astroquery + pyavm):
    python register.py <feed_dir> <work_dir> <image_subdir> id [id ...]

For each id in <feed_dir>/<image_subdir>/<id>/ (e.g. _hold_nowcs) it tries references in order:
  1. the verified press image with AVM (fullres_match_url in the assessment CSV)
  2. survey FITS with exact WCS: PS1 r (dec > -30), SDSS r, DSS2 red, 2MASS K, WISE 3.4 (SkyView / PS1 cutouts)
  3. Chandra's own CDA HiPS (X-ray; same photons as the press image)
and fits a TAN WCS from SIFT + RANSAC (similarity) matches. Accepted fits go to
<feed_dir>/wcs/<id>.fits (FITS pixel convention, IMAGEW/IMAGEH = image size) and every
attempt is logged to <feed_dir>/wcs/_register_log.csv.
"""
import csv, io, json, math, os, re, sys, time, urllib.parse, urllib.request, warnings
import numpy as np
import cv2
from PIL import Image
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import fit_wcs_from_points, proj_plane_pixel_scales
from astropy.coordinates import SkyCoord
import astropy.units as u

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hips_sample

warnings.filterwarnings('ignore')
Image.MAX_IMAGE_PIXELS = None
UA = {'User-Agent': 'wwt-core-catalogs chandra feed (registration)'}
MAXWORK = 3000          # max working image size (px) for feature matching
MIN_INLIERS = 20


def get(url, path=None, timeout=300):
    if path and os.path.exists(path) and os.path.getsize(path) > 0:
        return open(path, 'rb').read()
    for k in range(4):
        try:
            d = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
            if path:
                open(path, 'wb').write(d)
            return d
        except Exception as e:
            err = e
            time.sleep(3 * (k + 1))
    raise err


def to_gray8(a):
    a = np.asarray(a, dtype=np.float32)
    if a.ndim == 3:
        a = a[..., :3].mean(axis=2)
    a = np.nan_to_num(a, nan=0.0)
    lo, hi = np.percentile(a, [1, 99.7])
    if hi <= lo:
        hi = lo + 1
    a = np.clip((a - lo) / (hi - lo), 0, 1)
    a = np.arcsinh(10 * a) / np.arcsinh(10)
    return (a * 255).astype(np.uint8)


def parse_coords(s):
    m = re.search(r'RA\s*(\d+)h\s*(\d+)m\s*([\d.]+)s\s*\|\s*Dec\s*([+\-−]?)\s*(\d+)\D+(\d+)\D+([\d.]+)', s or '')
    if not m:
        return None
    ra = (int(m.group(1)) + int(m.group(2)) / 60 + float(m.group(3)) / 3600) * 15
    sg = -1 if m.group(4) in ('-', '−') else 1
    return ra, sg * (int(m.group(5)) + int(m.group(6)) / 60 + float(m.group(7)) / 3600)


def parse_fov_deg(s):
    s = (s or '').replace('´', "'")
    m = re.search(r'([\d.]+)\s*(?:by|x|×)\s*([\d.]+)\s*(arcmin|arcsec|deg)', s, re.I) or \
        re.search(r'([\d.]+)\s*(arcmin|arcsec|arc ?min|arc ?sec|deg)', s, re.I)
    if not m:
        return None
    v = float(m.group(1)); unit = m.groups()[-1].lower().replace(' ', '')
    return v / 3600 if unit.startswith('arcsec') else v if unit.startswith('deg') else v / 60


def position_avm(cachedir):
    """Centre from any AVM set (even a stale one written for another crop)."""
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from corepipe.chandra import avm_sets
    for f in ('image.tif', 'avm.jpg'):
        p = os.path.join(cachedir, f)
        if not os.path.exists(p):
            continue
        for s in avm_sets(p):
            try:
                rv = [float(re.sub(r'[^0-9eE+\-.]', '', x)) for x in s['Spatial.ReferenceValue'][:2]]
                return rv[0], rv[1]
            except Exception:
                pass
    return None


# ---------------------------------------------------------------- references
def ref_press(url, work):
    """djangoplicity press image: returns (gray image top-down, WCS FITS-convention, label)."""
    m = re.match(r'(https?://[^ ]+/images/)([^/]+)/', url)
    base, iid = m.group(1), m.group(2)
    j = json.loads(get(base + iid + '/api/json/', os.path.join(work, iid + '.json')))
    res = {r.get('ResourceType'): r for r in j.get('Resources', []) or []}
    pick = None
    for k in ('Large', 'Original'):
        r = res.get(k)
        if r and r.get('URL', '').lower().endswith(('.jpg', '.jpeg')):
            pick = r; break
    if pick is None:
        r = res.get('Original')
        if r and (r.get('FileSize') or 0) < 400e6:
            pick = r
    if pick is None:
        return None
    ext = pick['URL'].rsplit('.', 1)[-1]
    path = os.path.join(work, f'{iid}_ref.{ext}')
    get(pick['URL'], path, timeout=900)
    im = Image.open(path)
    W, H = im.size
    f = lambda v: float(str(v).strip(';, '))
    ra, dec = [f(x) for x in j['Spatial.ReferenceValue']]
    rw, rh = [f(x) for x in j['Spatial.ReferenceDimension']]
    px, py = [f(x) for x in j['Spatial.ReferencePixel']]
    sc = j['Spatial.Scale']
    sx = f(sc[0]); sy = f(sc[1]) if sc[1] not in (None, '') else abs(sx)
    rot = f(j.get('Spatial.Rotation') or 0)
    k = W / rw
    w = WCS(naxis=2)
    w.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [(px - 0.5) * k + 0.5, (py - 0.5) * k + 0.5]
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    w.wcs.cd = np.array([[sx * cr, -sy * sr], [sx * sr, sy * cr]]) / k
    return np.asarray(im.convert('L')), w, f'press:{iid}'


def ref_skyview(survey, ra, dec, fov, npix, work=None):
    q = urllib.parse.urlencode({'Survey': survey, 'Position': f'{ra:.6f},{dec:.6f}', 'Size': f'{fov:.6f}',
                                'Pixels': npix, 'Projection': 'Tan', 'Coordinates': 'J2000', 'Return': 'FITS'})
    path = os.path.join(work, 'sv_' + re.sub(r'\W', '', survey) + f'_{ra:.4f}_{dec:.4f}_{fov:.4f}.fits') if work else None
    d = get('https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl?' + q, path, timeout=120)
    if not d.startswith(b'SIMPLE'):
        return None
    h = fits.open(io.BytesIO(d))[0]
    if h.data is None or not np.isfinite(h.data).any() or np.nanstd(h.data) == 0:
        return None
    return to_gray8(h.data[::-1]), WCS(h.header), f'skyview:{survey}'


def ref_ps1(ra, dec, fov, work):
    size = int(round(fov * 3600 / 0.25))
    if size > 5000:
        return None
    t = get(f'https://ps1images.stsci.edu/cgi-bin/ps1filenames.py?ra={ra}&dec={dec}&filters=r').decode()
    rows = [l.split() for l in t.strip().splitlines()[1:]]
    if not rows:
        return None
    fn = rows[0][7]
    url = (f'https://ps1images.stsci.edu/cgi-bin/fitscut.cgi?ra={ra}&dec={dec}&size={size}&format=fits&red={fn}')
    d = get(url, os.path.join(work, f'ps1_{ra:.4f}_{dec:.4f}_{size}.fits'))
    h = fits.open(io.BytesIO(d))[0]
    if h.data is None or not np.isfinite(h.data).any():
        return None
    return to_gray8(h.data[::-1]), WCS(h.header), 'ps1:r'


def ref_cda(ra, dec, fov, work):
    npix = int(min(2500, max(400, fov * 3600 / 0.25)))
    rgb, w = hips_sample.sample('https://cdaftp.cfa.harvard.edu/cxc-hips', 11, 512, ra, dec, fov, npix,
                                os.path.join(work, 'cda_tiles'), 'png')
    if rgb.max() == 0:
        return None
    return to_gray8(rgb), w, 'cda-hips'


def ref_legacy(ra, dec, fov, work):
    pixscale = max(0.262, fov * 3600 / 3000)
    size = int(min(3000, fov * 3600 / pixscale))
    url = (f'https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=ls-dr10'
           f'&pixscale={pixscale:.3f}&size={size}&bands=r')
    d = get(url, os.path.join(work, f'ls_{ra:.4f}_{dec:.4f}_{size}_{pixscale:.3f}.fits'))
    if not d.startswith(b'SIMPLE'):
        return None
    h = fits.open(io.BytesIO(d))[0]
    data = h.data if h.data.ndim == 2 else h.data[0]
    if not np.isfinite(data).any() or np.count_nonzero(data) < 0.5 * data.size:
        return None
    hdr = h.header.copy()
    w = WCS(hdr).celestial
    return to_gray8(data[::-1]), w, 'legacy:r'


HIPS = {
    'sdss': ('https://irsa.ipac.caltech.edu/data/hips/CDS/SDSS/DR9/color', 10, 'jpg'),
    'dss': ('https://irsa.ipac.caltech.edu/data/hips/CDS/DSS2/red', 9, 'jpg'),
    'irac1': ('https://irsa.ipac.caltech.edu/data/hips/CDS/SPITZER/IRAC1', 9, 'jpg'),
    '2mass': ('https://irsa.ipac.caltech.edu/data/hips/CDS/2MASS/K', 9, 'jpg'),
    'wise': ('https://irsa.ipac.caltech.edu/data/hips/CDS/AllWISE/W1', 8, 'jpg'),
}


def ref_hips(key, ra, dec, fov, work):
    url, order, fmt = HIPS[key]
    native = 3600 * math.degrees(math.sqrt(4 * math.pi / (12 * 4 ** (order + 9))))
    npix = int(min(2000, max(300, fov * 3600 / native)))
    rgb, w = hips_sample.sample(url, order, 512, ra, dec, fov, npix, os.path.join(work, 'hips_' + key), fmt)
    g = rgb.mean(axis=2)
    if (g > 0).mean() < 0.5 or g.std() < 1:
        return None
    return to_gray8(rgb), w, f'hips:{key}'


# ---------------------------------------------------------------- matching
def match(C, cs, R, rs, floor=None):
    """C: chandra gray (top-down) at its working scale cs (arcsec/px, estimate); R: ref gray, rs.
    `floor` forces a coarser common working scale. Returns (A, inlier mask, pc, pr, n_good)."""
    ts = max(cs, rs, floor or 0)
    zc = min(cs / ts, MAXWORK / max(C.shape))
    zr = min(rs / ts, MAXWORK / max(R.shape))
    Cw = cv2.resize(C, None, fx=zc, fy=zc, interpolation=cv2.INTER_AREA) if zc < 1 else C
    Rw = cv2.resize(R, None, fx=zr, fy=zr, interpolation=cv2.INTER_AREA) if zr < 1 else R
    zc = min(zc, 1.0); zr = min(zr, 1.0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    Cw, Rw = clahe.apply(Cw), clahe.apply(Rw)
    s_exp = (cs / zc) / (rs / zr)
    res = _match_sift(Cw, Rw, s_exp)
    if floor is None and (res is None or res[1].sum() < MIN_INLIERS):  # point search only on the sharp pass
        pm = match_points(Cw, Rw, s_exp)
        if pm is not None and (res is None or len(pm[1]) > res[1].sum()):
            A, pcp, prp = pm
            return A, np.ones(len(pcp), bool), pcp / zc, prp / zr, len(pcp)
    if res is None:
        return None
    A, full, pc, pr, ng = res
    return A, full, pc / zc, pr / zr, ng


def _match_sift(Cw, Rw, s_exp):
    sift = cv2.SIFT_create(nfeatures=30000)
    k1, d1 = sift.detectAndCompute(Cw, None)
    k2, d2 = sift.detectAndCompute(Rw, None)
    if d1 is None or d2 is None or len(k1) < 10 or len(k2) < 10:
        return None
    mm = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    good = [a for a, b in (x for x in mm if len(x) == 2) if a.distance < 0.8 * b.distance]
    # one-to-one: many Chandra keypoints matching the same bright reference star otherwise
    # let RANSAC "win" with a near-zero-scale transform
    best = {}
    for g in good:
        if g.trainIdx not in best or g.distance < best[g.trainIdx].distance:
            best[g.trainIdx] = g
    good = list(best.values())
    if len(good) < 12:
        return None
    pc = np.float32([k1[g.queryIdx].pt for g in good])
    pr = np.float32([k2[g.trainIdx].pt for g in good])
    pool = np.ones(len(good), bool)
    for _ in range(4):
        if pool.sum() < 12:
            return None
        A, inl = cv2.estimateAffinePartial2D(pc[pool], pr[pool], method=cv2.RANSAC, ransacReprojThreshold=3.0,
                                             maxIters=20000, confidence=0.999)
        if A is None:
            return None
        s = math.hypot(A[0, 0], A[1, 0])
        full = np.zeros(len(good), bool)
        full[np.flatnonzero(pool)[inl.ravel().astype(bool)]] = True
        if 0.25 < s / s_exp < 4:
            return A, full, pc, pr, len(good)
        pool &= ~full  # implausible scale: discard this consensus set and look again
    return None


def detect_points(img, n):
    """Point sources: peaks of a difference-of-Gaussians, brightest n."""
    f = img.astype(np.float32)
    d = cv2.GaussianBlur(f, (0, 0), 1.2) - cv2.GaussianBlur(f, (0, 0), 5.0)
    mx = cv2.dilate(d, np.ones((9, 9), np.uint8))
    thr = np.percentile(d, 99.0)
    ys, xs = np.nonzero((d >= mx) & (d > thr) & (d > 0))
    if len(xs) == 0:
        return np.zeros((0, 2), np.float32)
    v = d[ys, xs]
    o = np.argsort(-v)[:n]
    return np.float32(np.stack([xs[o], ys[o]], axis=1))


def _render(pts, shape, sigma=1.5):
    m = np.zeros(shape, np.float32)
    xi = np.round(pts[:, 0]).astype(int); yi = np.round(pts[:, 1]).astype(int)
    ok = (xi >= 0) & (yi >= 0) & (xi < shape[1]) & (yi < shape[0])
    m[yi[ok], xi[ok]] = 1.0
    return cv2.GaussianBlur(m, (0, 0), sigma)


def match_points(Cw, Rw, s_exp, rotations=(0.0, -3.0, 3.0, 180.0)):
    """Asterism-free point-pattern match: grid over scale/rotation, FFT correlation for translation.
    Returns (A 2x3 Cw->Rw, pc, pr) for paired points, or None."""
    pc_all = detect_points(Cw, 150)
    pr_all = detect_points(Rw, 300)
    if len(pc_all) < 10 or len(pr_all) < 10:
        return None
    q = min(1.0, 768 / max(Rw.shape))
    H, W = int(Rw.shape[0] * q) + 1, int(Rw.shape[1] * q) + 1
    FR = np.fft.rfft2(_render(pr_all * q, (H, W)))
    cC = np.array([Cw.shape[1] / 2, Cw.shape[0] / 2], np.float32)
    best = []
    for s in s_exp * np.geomspace(1 / 2.5, 2.5, 25):
        for rot in rotations:
            c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            M = s * np.array([[c, -sn], [sn, c]], np.float32)
            p = (pc_all - cC) @ M.T * q + np.array([W / 2, H / 2], np.float32)
            corr = np.fft.irfft2(FR * np.conj(np.fft.rfft2(_render(p, (H, W)))), s=(H, W))
            k = np.argmax(corr)
            dy, dx = divmod(k, W)
            dy = dy - H if dy > H / 2 else dy
            dx = dx - W if dx > W / 2 else dx
            best.append((corr.flat[k], s, rot, dx, dy, M))
    best.sort(key=lambda b: -b[0])
    out = None
    for val, s, rot, dx, dy, M in best[:6]:
        t = np.array([W / 2 + dx, H / 2 + dy], np.float32) / q
        pred = (pc_all - cC) @ M.T + t
        d2 = ((pred[:, None, :] - pr_all[None, :, :]) ** 2).sum(-1)
        j = d2.argmin(1)
        tol = max(2.5, 1.5 / q)
        ok = d2[np.arange(len(j)), j] < tol ** 2
        # unique partners only
        _, first = np.unique(j[ok], return_index=True)
        ii = np.flatnonzero(ok)[first]
        if len(ii) < 8:
            continue
        A, inl = cv2.estimateAffinePartial2D(pc_all[ii], pr_all[j[ii]], method=cv2.RANSAC, ransacReprojThreshold=tol)
        if A is None:
            continue
        inl = inl.ravel().astype(bool)
        # pairs expected by chance across the whole scale/rotation search (~33*4*6 trials)
        n_rand = len(pc_all) * len(pr_all) * math.pi * tol ** 2 / (Rw.shape[0] * Rw.shape[1])
        need = max(10, n_rand + 5 * math.sqrt(max(n_rand, 1)) + 4)
        if inl.sum() >= need and (out is None or inl.sum() > out[0]):
            out = (int(inl.sum()), A, pc_all[ii][inl], pr_all[j[ii]][inl])
    if out is None:
        return None
    return out[1], out[2], out[3]


def solve(C, Wfull, Hfull, cs_est, ref, alt_scales=()):
    # Smoothed press images match raw survey/X-ray data better at coarser scales: retry blurred.
    msgs = []
    for coarsen in (1, 2, 4):
        sol, msg = _solve(C, Wfull, Hfull, cs_est, ref, coarsen, alt_scales)
        msgs.append(f'x{coarsen} {msg}')
        if sol:
            return sol, ' / '.join(msgs)
    return None, ' / '.join(msgs)


def _solve(C, Wfull, Hfull, cs_est, ref, coarsen, alt_scales=()):
    R, rw, label = ref
    rs = proj_plane_pixel_scales(rw)[0] * 3600
    if coarsen > 1:
        # pretend both images are coarser so match() downsamples them to a common, blurrier grid
        out = match(C, cs_est, R, rs, floor=max(cs_est, rs) * coarsen)
    else:
        out = match(C, cs_est, R, rs)
    if out is None:
        return None, f'{label}: too few matches'
    A, inl, pc, pr, ngood = out
    n = int(inl.sum())
    scale = math.hypot(A[0, 0], A[1, 0])
    if n < MIN_INLIERS and not (n >= 12 and n >= 0.4 * ngood):
        return None, f'{label}: {n} inliers of {ngood}'
    Hr = R.shape[0]
    sky = rw.pixel_to_world(pr[inl, 0], (Hr - 1) - pr[inl, 1])
    pcs = pc[inl] * (Wfull / C.shape[1])
    CW = fit_wcs_from_points((pcs[:, 0], (Hfull - 1) - pcs[:, 1]), sky, projection='TAN')
    res = CW.pixel_to_world(pcs[:, 0], (Hfull - 1) - pcs[:, 1]).separation(sky).arcsec
    rms = float(np.sqrt(np.mean(res ** 2)))
    px = proj_plane_pixel_scales(CW)[0] * 3600
    # sanity: the fitted pixel scale must be within 3x of the fact-sheet estimate and RMS < 1.5 image px
    full_est = cs_est * C.shape[1] / Wfull
    scale_ok = (1 / 3 < px / full_est < 3) or any(abs(px / a - 1) < 0.15 for a in alt_scales)
    ok = px > 1e-3 and n >= 12 and scale_ok and rms < max(2 * px, 1.2 * rs * coarsen)
    info = dict(ref=label, inliers=n, matches=ngood, rms_arcsec=round(rms, 3), px_arcsec=round(px, 4),
                rms_px=round(rms / px, 2), scale_vs_factsheet=round(px / full_est, 2))
    if not ok:
        return None, f'{label}: rejected {info}'
    return (CW, info), f'{label}: ok {info}'


def main():
    feed, work, sub = sys.argv[1], sys.argv[2], sys.argv[3]
    ids = sys.argv[4:]
    os.makedirs(work, exist_ok=True)
    wdir = os.path.join(feed, 'wcs'); os.makedirs(wdir, exist_ok=True)
    rows = {r['release'].replace('/', '-'): r for r in
            csv.DictReader(open(os.path.join(feed, '_assessment', 'chandra_assessment.csv'), encoding='utf-8'))
            if r['set'] == 'a'}
    logp = os.environ.get('REGLOG') or os.path.join(wdir, '_register_log.csv')
    new = not os.path.exists(logp)
    logf = open(logp, 'a', newline='', encoding='utf-8'); lw = csv.writer(logf)
    if new:
        lw.writerow(['id', 'result', 'ref', 'inliers', 'rms_arcsec', 'px_arcsec', 'rms_px', 'scale_vs_factsheet', 'tried'])
    for uid in ids:
        cdir = os.path.join(feed, sub, uid)
        if not os.path.isdir(cdir):
            print(uid, 'not fetched'); continue
        md = json.load(open(os.path.join(cdir, 'metadata.json'), encoding='utf-8'))
        img = Image.open(os.path.join(cdir, 'image.' + md['toasty_image_extension']))
        Wf, Hf = img.size
        z = min(1.0, 4000 / max(Wf, Hf))
        img.draft('L', (int(Wf * z), int(Hf * z)))
        C = to_gray8(np.asarray(img.convert('L').resize((int(Wf * z), int(Hf * z)), Image.LANCZOS)))
        del img
        fov = parse_fov_deg(md['facts'].get('Scale', ''))
        row = rows.get(uid, {})
        seeds = []
        for s in (position_avm(cdir), parse_coords(md['facts'].get('Coordinates (J2000)', ''))):
            if s and -90 <= s[1] <= 90 and all(abs(s[0] - q[0]) * math.cos(math.radians(s[1])) * 60 > (fov or 0.05) * 20
                                               or abs(s[1] - q[1]) * 60 > (fov or 0.05) * 20 for q in seeds):
                seeds.append(s)
        alt_scales = []
        try:
            from corepipe.chandra import avm_sets
            for s in avm_sets(os.path.join(cdir, 'image.' + md['toasty_image_extension'])):
                sc = s.get('Spatial.Scale'); rd = s.get('Spatial.ReferenceDimension')
                if sc and rd:
                    alt_scales.append(abs(float(re.sub(r'[^0-9eE+.-]', '', sc[0]))) * 3600 *
                                      float(re.sub(r'[^0-9eE+.-]', '', rd[0])) / Wf)
        except Exception:
            pass
        if not fov and alt_scales:
            fov = alt_scales[0] * Wf / 3600  # fact sheet gives no scale: trust the AVM's, roughly
        if not seeds or not fov:
            print(uid, 'no seed position/scale'); lw.writerow([uid, 'no-seed', '', '', '', '', '', '', '']); continue
        cs_est = fov * 3600 / C.shape[1]
        rfov = min(max(fov * 1.8, 2 / 60), 1.0)
        layers = row.get('nonchandra_layers', '')
        xray_only = not layers.strip()
        ir = bool(re.search(r'IR:|Spitzer|JWST|WISE|2MASS|Herschel', layers))
        press = [('press', u.strip()) for u in (row.get('fullres_match_url') or '').split(' | ') if u.strip()]
        optical = [('legacy', None), ('ps1', None), ('hips', 'sdss'), ('skyview', 'DSS2 Red')]
        infra = [('hips', 'irac1'), ('hips', '2mass'), ('hips', 'wise')]
        if xray_only:
            refs = [('cda', None)] + optical
        elif ir:
            refs = press + infra + optical + [('cda', None)]
        else:
            refs = press + optical + infra + [('cda', None)]
        tried = []
        result = None
        for si, (ra, dec) in enumerate(seeds):
            for kind, arg in refs:
                if kind == 'press' and si > 0:
                    continue
                if kind == 'ps1' and dec < -30:
                    continue
                try:
                    if kind == 'press':
                        ref = ref_press(arg, work)
                    elif kind == 'ps1':
                        ref = ref_ps1(ra, dec, rfov, work)
                    elif kind == 'legacy':
                        ref = ref_legacy(ra, dec, rfov, work)
                    elif kind == 'hips':
                        ref = ref_hips(arg, ra, dec, rfov, work)
                    elif kind == 'skyview':
                        ref = ref_skyview(arg, ra, dec, rfov, 1500, work)
                    else:
                        ref = ref_cda(ra, dec, rfov, work)
                except Exception as e:
                    tried.append(f'{kind}:{arg}: error {str(e)[:80]}'); continue
                if ref is None:
                    tried.append(f'{kind}:{arg}: no data'); continue
                sol, msg = solve(C, Wf, Hf, cs_est, ref, alt_scales)
                tried.append(f'seed{si} ' + msg)
                if sol:
                    result = sol; break
            if result:
                break
        if result:
            CW, info = result
            hdr = CW.to_header()
            hdr['IMAGEW'] = Wf; hdr['IMAGEH'] = Hf
            hdr['WCSSRC'] = info['ref'][:60]
            hdr['NMATCH'] = info['inliers']; hdr['RMSARCS'] = info['rms_arcsec']
            fits.PrimaryHDU(header=hdr).writeto(os.path.join(wdir, uid + '.fits'), overwrite=True)
            lw.writerow([uid, 'ok', info['ref'], info['inliers'], info['rms_arcsec'], info['px_arcsec'], info['rms_px'],
                         info['scale_vs_factsheet'], ' || '.join(tried)])
            print(uid, 'OK', info)
        else:
            lw.writerow([uid, 'failed', '', '', '', '', '', '', ' || '.join(tried)])
            print(uid, 'FAILED', ' || '.join(tried)[:300])
        logf.flush()
        sys.stdout.flush()


if __name__ == '__main__':
    main()
