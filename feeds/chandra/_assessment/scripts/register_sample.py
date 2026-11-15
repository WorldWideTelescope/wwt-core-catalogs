"""Register a Chandra composite (no AVM) against a full-res AVM-tagged reference.

usage: python -I register_sample.py chandra_img ref_img ref_api_json out_prefix
Writes <out_prefix>_wcs.fits (header-only WCS for the Chandra image) and prints diagnostics.
"""
import sys, json, math
import numpy as np, cv2
from PIL import Image
from astropy.wcs import WCS
from astropy.wcs.utils import fit_wcs_from_points, proj_plane_pixel_scales
from astropy.coordinates import SkyCoord
from astropy.io import fits
import astropy.units as u

Image.MAX_IMAGE_PIXELS = None
cimg, rimg, rjson, out = sys.argv[1:5]


def gray(path):
    a = np.asarray(Image.open(path).convert('L'), dtype=np.uint8)
    return a


def avm_wcs(j, w, h):
    f = lambda v: float(str(v).strip(';, '))
    ra, dec = [f(x) for x in j['Spatial.ReferenceValue']]
    rw, rh = [f(x) for x in j['Spatial.ReferenceDimension']]
    px, py = [f(x) for x in j['Spatial.ReferencePixel']]
    sx, sy = [f(x) for x in j['Spatial.Scale']]
    rot = f(j.get('Spatial.Rotation', 0) or 0)
    k = w / rw  # image may be a resampled version of the reference dimension
    W = WCS(naxis=2)
    W.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    W.wcs.crval = [ra, dec]
    # AVM pixel coords: origin at lower-left (FITS-like), images are stored top-down
    W.wcs.crpix = [px * k, py * k]
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    W.wcs.cd = np.array([[sx * cr, -sy * sr], [sx * sr, sy * cr]]) / k
    return W


C = gray(cimg)
Rf = gray(rimg)
j = json.load(open(rjson))
RW = avm_wcs(j, Rf.shape[1], Rf.shape[0])
ref_scale = proj_plane_pixel_scales(RW)[0] * 3600
# bring reference roughly to the Chandra image scale (seed from fact sheet: given as argv[5] arcsec/px)
c_scale = float(sys.argv[5])
z = ref_scale / c_scale
Rs = cv2.resize(Rf, None, fx=z, fy=z, interpolation=cv2.INTER_AREA)
sift = cv2.SIFT_create(nfeatures=20000)
k1, d1 = sift.detectAndCompute(C, None)
k2, d2 = sift.detectAndCompute(Rs, None)
m = cv2.BFMatcher().knnMatch(d1, d2, k=2)
good = [a for a, b in m if a.distance < 0.75 * b.distance]
p1 = np.float32([k1[g.queryIdx].pt for g in good])
p2 = np.float32([k2[g.trainIdx].pt for g in good]) / z
A, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=3.0 / z)
inl = inl.ravel().astype(bool)
print(f'SIFT matches {len(good)}, RANSAC inliers {inl.sum()}')
s = math.hypot(A[0, 0], A[1, 0]); ang = math.degrees(math.atan2(A[1, 0], A[0, 0]))
print(f'similarity: scale {s:.4f} (ref px per chandra px), rotation {ang:.3f} deg')
# sky positions of inlier Chandra pixels via the reference WCS.
# image row 0 is the top; AVM/FITS y runs upward -> flip y for the reference
H = Rf.shape[0]
q = p2[inl]
sky = RW.pixel_to_world(q[:, 0], (H - 1) - q[:, 1])
ci = p1[inl]
Hc = C.shape[0]
CW = fit_wcs_from_points((ci[:, 0], (Hc - 1) - ci[:, 1]), sky, projection='TAN')
pred = CW.pixel_to_world(ci[:, 0], (Hc - 1) - ci[:, 1])
res = pred.separation(sky).arcsec
cen = CW.pixel_to_world(C.shape[1] / 2, C.shape[0] / 2)
sc = proj_plane_pixel_scales(CW) * 3600
print(f'fitted Chandra WCS: centre {cen.ra.deg:.5f} {cen.dec.deg:.5f}, scale {sc[0]:.4f}"/px, '
      f'FOV {sc[0] * C.shape[1] / 60:.3f} arcmin; residual rms {np.sqrt(np.mean(res ** 2)):.3f}" median {np.median(res):.3f}"')
hdr = CW.to_header(relax=True)
hdr['NAXIS'] = 2; hdr['NAXIS1'] = C.shape[1]; hdr['NAXIS2'] = C.shape[0]
fits.PrimaryHDU(header=hdr).writeto(out + '_wcs.fits', overwrite=True)
print('wrote', out + '_wcs.fits')
