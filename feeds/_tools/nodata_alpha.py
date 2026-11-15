"""Make black no-data borders transparent in toasty study pyramids (LXY PNG tiles).

    python nodata_alpha.py survey [--preview DIR] PYRAMID_DIR...
    python nodata_alpha.py apply --threshold T PYRAMID_DIR...

Works from the tiles, so no source image is needed. The deepest level holds the
source pixels losslessly, so:

1. Stitch the deepest level (cropped to the tiles present).
2. Candidate = transparent (outside the image) or black (max(R,G,B) <= T).
3. Keep candidates connected to the outside: the crop border, or the padding
   toasty already made transparent. Dark sky enclosed by data is never touched.
4. Write that alpha back into the deepest tiles, then rebuild every lower level
   by 2x2 alpha-weighted averaging.

Every tile that existed before is rewritten. Tiles that end up fully transparent
are still written, because the old opaque copies are already on Azure and must
be overwritten. Survey mode uses a level about 2048 px across and changes nothing.
"""

import argparse
import os
import re
import sys

import numpy as np
import PIL.Image as I
from scipy import ndimage

I.MAX_IMAGE_PIXELS = None
TILE = 256
PAT = re.compile(r"^L(\d+)X(\d+)Y(\d+)\.png$")


def tiles_by_level(d):
    lv = {}
    for f in os.listdir(d):
        m = PAT.match(f)
        if m:
            l, x, y = map(int, m.groups())
            lv.setdefault(l, set()).add((x, y))
    return lv


def load_rgba(path):
    im = I.open(path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    return np.asarray(im)


def stitch(d, level, coords):
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    x0, y0 = min(xs), min(ys)
    W = (max(xs) - x0 + 1) * TILE
    H = (max(ys) - y0 + 1) * TILE
    a = np.zeros((H, W, 4), np.uint8)
    for x, y in coords:
        t = load_rgba(os.path.join(d, f"L{level}X{x}Y{y}.png"))
        a[(y - y0) * TILE:(y - y0 + 1) * TILE, (x - x0) * TILE:(x - x0 + 1) * TILE] = t
    return a, x0, y0


def outside_mask(a, threshold):
    cand = (a[..., 3] == 0) | (a[..., :3].max(axis=2) <= threshold)
    lab, _ = ndimage.label(cand)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    edge = edge[edge > 0]
    # Components touching already-transparent padding also count as outside.
    pad = np.unique(lab[a[..., 3] == 0])
    keep = np.union1d(edge, pad[pad > 0])
    return np.isin(lab, keep)


def survey(dirs, preview):
    for d in dirs:
        lv = tiles_by_level(d)
        if not lv:
            continue
        top = max(lv)
        level = max(min(lv), top - 3) if top > 3 else top
        while level > 0 and len(lv[level]) > 64:
            level -= 1
        a, _, _ = stitch(d, level, lv[level])
        inside = a[..., 3] > 0
        if not inside.any():
            continue
        m = outside_mask(a, 0)
        frac = (m & inside).sum() / inside.sum()
        print(f"{frac:7.3f}  {os.path.basename(os.path.normpath(d))}", flush=True)
        if preview and frac > 0.005:
            vis = a[..., :3].copy()
            vis[a[..., 3] == 0] = (128, 128, 128)
            vis[m & inside] = (255, 0, 255)
            v = I.fromarray(vis)
            v.thumbnail((400, 400))
            v.save(os.path.join(preview, os.path.basename(os.path.normpath(d)) + ".png"))


def downsample(children):
    """children: 512x512x4 uint8 -> 256x256x4, alpha-weighted mean."""
    c = children.astype(np.float32).reshape(TILE, 2, TILE, 2, 4)
    al = c[..., 3:4]
    asum = al.sum(axis=(1, 3))
    rgb = (c[..., :3] * al).sum(axis=(1, 3)) / np.maximum(asum, 1e-6)
    out = np.zeros((TILE, TILE, 4), np.float32)
    out[..., :3] = rgb
    out[..., 3] = asum[..., 0] / 4
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def apply(dirs, threshold):
    for d in dirs:
        lv = tiles_by_level(d)
        top = max(lv)
        a, x0, y0 = stitch(d, top, lv[top])
        m = outside_mask(a, threshold)
        changed = m & (a[..., 3] > 0)
        print(f"{os.path.basename(os.path.normpath(d))}: masking {changed.sum() / max(1, (a[..., 3] > 0).sum()):.3f} "
              f"of image pixels (T={threshold})", flush=True)
        a[m] = 0
        del m, changed
        tiles = {}
        for x, y in lv[top]:
            t = a[(y - y0) * TILE:(y - y0 + 1) * TILE, (x - x0) * TILE:(x - x0 + 1) * TILE]
            tiles[(x, y)] = t
            I.fromarray(t, "RGBA").save(os.path.join(d, f"L{top}X{x}Y{y}.png"), optimize=False)
        empty = np.zeros((TILE, TILE, 4), np.uint8)
        for level in range(top - 1, min(lv) - 1, -1):
            parents = {}
            for (x, y) in lv.get(level, set()):
                kids = np.zeros((2 * TILE, 2 * TILE, 4), np.uint8)
                for dx in (0, 1):
                    for dy in (0, 1):
                        k = tiles.get((2 * x + dx, 2 * y + dy), empty)
                        kids[dy * TILE:(dy + 1) * TILE, dx * TILE:(dx + 1) * TILE] = k
                p = downsample(kids)
                parents[(x, y)] = p
                I.fromarray(p, "RGBA").save(os.path.join(d, f"L{level}X{x}Y{y}.png"))
            tiles = parents
        del a, tiles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["survey", "apply"])
    ap.add_argument("--threshold", type=int, default=0)
    ap.add_argument("--preview")
    ap.add_argument("dirs", nargs="+")
    args = ap.parse_args()
    # A directory without tiles is treated as a parent of pyramid directories.
    dirs = []
    for d in args.dirs:
        if tiles_by_level(d):
            dirs.append(d)
        else:
            dirs += sorted(os.path.join(d, s) for s in os.listdir(d) if os.path.isdir(os.path.join(d, s)))
    args.dirs = dirs
    if args.mode == "survey":
        survey(args.dirs, args.preview)
    else:
        apply(args.dirs, args.threshold)


if __name__ == "__main__":
    main()
