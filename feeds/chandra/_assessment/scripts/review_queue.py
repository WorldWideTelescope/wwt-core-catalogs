"""Decide what gets tiled after register.py, and queue it.

usage (wwt env python, from feeds/chandra):  python review_queue.py [--apply]

Rules
- A registration (wcs/<id>.fits) is accepted unless:
  * multi-panel suspect: wide image (aspect > 1.8) whose fitted width is > 1.6x the fact-sheet field
  * its centre is > max(2', field) from the fact-sheet position AND > that from every AVM centre
- Images already tiled from AVM (cache_done/) without an accepted registration keep their tiles
  only if the AVM centre is within max(1', field/2) of the fact sheet and the AVM field is within
  30% of the fact-sheet field; otherwise their tiles are moved to on-hold/.
- Accepted registrations are queued for (re)tiling: image dirs go to cache_todo/, stale
  processed/<id> output is moved to on-hold/<id>.avm/.
Writes wcs/_review.csv. Without --apply nothing is moved.
"""
import csv, glob, json, math, os, re, shutil, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corepipe.chandra import avm_sets, best_avm  # noqa: E402
from register import parse_coords, parse_fov_deg  # noqa: E402
from astropy.io import fits  # noqa: E402
from astropy.wcs import WCS  # noqa: E402
from astropy.coordinates import SkyCoord  # noqa: E402
import astropy.units as u  # noqa: E402
from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
APPLY = '--apply' in sys.argv


def sep_arcmin(a, b):
    return SkyCoord(a[0] * u.deg, a[1] * u.deg).separation(SkyCoord(b[0] * u.deg, b[1] * u.deg)).arcmin


def avm_centres(path):
    out = []
    for s in avm_sets(path):
        try:
            c = tuple(float(re.sub(r'[^0-9eE+.-]', '', x)) for x in s['Spatial.ReferenceValue'][:2])
            if 0 <= c[0] <= 360 and -90 <= c[1] <= 90:
                out.append(c)
        except Exception:
            pass
    return out


def where(uid):
    for sub in ('_hold_nowcs', 'cache_done', 'cache_todo', 'cache_failed'):
        if os.path.isdir(os.path.join(sub, uid)):
            return sub
    return None


rows = []
ids = sorted(set(os.listdir('_hold_nowcs')) | set(os.listdir('cache_done')))
for uid in ids:
    sub = where(uid)
    d = os.path.join(sub, uid)
    md = json.load(open(os.path.join(d, 'metadata.json'), encoding='utf-8'))
    img = os.path.join(d, 'image.' + md['toasty_image_extension'])
    W, H = Image.open(img).size
    fc = parse_coords(md['facts'].get('Coordinates (J2000)', ''))
    ffov = parse_fov_deg(md['facts'].get('Scale', ''))
    ffov = ffov * 60 if ffov else None
    tol = max(2.0, ffov or 0)
    r = {'id': uid, 'where': sub, 'size': f'{W}x{H}', 'fact_fov_arcmin': round(ffov, 2) if ffov else ''}
    side = os.path.join('wcs', uid + '.fits')
    decision, why = None, ''
    if os.path.exists(side):
        h = fits.getheader(side)
        w = WCS(h)
        c = w.pixel_to_world(W / 2, H / 2)
        cen = (c.ra.deg, c.dec.deg)
        px = abs(w.pixel_scale_matrix[0, 0] ** 2 + w.pixel_scale_matrix[1, 0] ** 2) ** 0.5 * 60
        fov = px * W
        r.update(src=h.get('WCSSRC', ''), rms_arcsec=h.get('RMSARCS', ''), fit_fov_arcmin=round(fov, 2))
        offs = [sep_arcmin(cen, fc)] if fc else []
        offs += [sep_arcmin(cen, a) for a in avm_centres(img)]
        r['min_offset_arcmin'] = round(min(offs), 2) if offs else ''
        if W / H > 1.8 and ffov and fov > 1.6 * ffov:
            decision, why = 'hold', 'multi-panel suspect'
        elif offs and min(offs) > tol:
            decision, why = 'hold', 'registered centre far from fact sheet and AVM'
        else:
            decision, why = 'tile-registered', ''
    if decision is None and sub == 'cache_done':
        h, note = best_avm([img, os.path.join(d, 'avm.jpg')], W, H)
        if h is not None:
            w = WCS(h)
            c = w.pixel_to_world(W / 2, H / 2)
            fov = (abs(h['CD1_1'] * h['CD2_2'] - h['CD1_2'] * h['CD2_1'])) ** 0.5 * 60 * W
            off = sep_arcmin((c.ra.deg, c.dec.deg), fc) if fc else None
            r.update(src=note, fit_fov_arcmin=round(fov, 2), min_offset_arcmin=round(off, 2) if off is not None else '')
            if off is not None and off <= max(1.0, (ffov or 0) / 2) and ffov and abs(fov / ffov - 1) <= 0.3:
                decision, why = 'keep-avm', 'AVM agrees with fact sheet'
            else:
                decision, why = 'unpublish', 'unverified AVM disagrees with fact sheet'
    if decision is None:
        decision, why = 'hold', 'no registration'
    r.update(decision=decision, why=why)
    rows.append(r)

    if not APPLY:
        continue
    if decision == 'tile-registered':
        if sub == 'cache_done' and os.path.isdir(os.path.join('processed', uid)):
            os.makedirs('on-hold', exist_ok=True)
            shutil.move(os.path.join('processed', uid), os.path.join('on-hold', uid + '.avm'))
        shutil.move(d, os.path.join('cache_todo', uid))
    elif decision == 'unpublish' and os.path.isdir(os.path.join('processed', uid)):
        os.makedirs('on-hold', exist_ok=True)
        shutil.move(os.path.join('processed', uid), os.path.join('on-hold', uid + '.avm'))
        shutil.move(d, os.path.join('_hold_nowcs', uid))

cols = ['id', 'decision', 'why', 'where', 'size', 'src', 'rms_arcsec', 'fit_fov_arcmin', 'fact_fov_arcmin', 'min_offset_arcmin']
with open(os.path.join('wcs', '_review.csv'), 'w', newline='', encoding='utf-8') as f:
    wr = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
    wr.writeheader()
    wr.writerows(rows)
from collections import Counter
print(Counter(r['decision'] for r in rows))
for r in rows:
    if r['decision'] in ('hold', 'unpublish') and r['why'] != 'no registration':
        print(r['id'], r['decision'], r['why'], r.get('fit_fov_arcmin'), r.get('fact_fov_arcmin'), r.get('min_offset_arcmin'))
