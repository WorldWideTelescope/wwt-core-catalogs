"""Tile NRAO images whose XMP carries complete AVM, without needing pyavm.

Usage (wwt env python, -I):
    python tile_avm.py <feed_dir> <batch.json>

batch.json is a list of
    {"id", "src", "title", "credit", "description", "credits_url",
     "band": "Radio"|"Multi", "xbands": "Visible,Radio" (Multi only)}

For each entry it parses avm:Spatial.* from the source's XMP, builds a WCS the
way pyavm's AVM.to_wcs does (CRVAL, CRPIX, CDELT, CROTA = Rotation, rescaled to
the real pixel size), then hands it to toasty's Builder.apply_avm_info, which
applies toasty's usual parity flip for JPEG-like data. Writes
processed/<id>/ (tiles, thumb, index_rel.wtml) and cache_done/<id>/metadata.json
(Title/Credit/Description, read by build_deliverable.py).
"""
import json
import os
import re
import sys

from astropy.wcs import WCS
from PIL import Image

from toasty.builder import Builder
from toasty.image import ImageLoader
from toasty.merge import averaging_merger, cascade_images
from toasty.pyramid import PyramidIO
from wwt_data_formats.enums import Bandpass

Image.MAX_IMAGE_PIXELS = None


def read_xmp(path):
    with open(path, "rb") as f:
        d = f.read()
    i = d.find(b"<x:xmpmeta")
    if i < 0:
        raise SystemExit(f"{path}: no XMP")
    return d[i:d.find(b"</x:xmpmeta>", i) + 12].decode("utf-8", "replace")


def spatial(x):
    out = {}
    for tag in ("CoordinateFrame", "Equinox", "CoordsystemProjection", "Rotation"):
        m = re.search(rf'avm:Spatial\.{tag}(?:="([^"]*)"|>\s*([^<]*)<)', x)
        if m:
            out[tag] = (m.group(1) or m.group(2) or "").strip()
    for tag in ("ReferenceValue", "ReferenceDimension", "ReferencePixel", "Scale", "CDMatrix"):
        m = re.search(rf"<avm:Spatial\.{tag}>(.*?)</avm:Spatial\.{tag}>", x, re.S)
        if m:
            out[tag] = [float(v) for v in re.findall(r"<rdf:li>([^<]*)</rdf:li>", m.group(1))]
    return out


class AVMShim:
    """Just enough of pyavm.AVM for toasty.Builder.apply_avm_info."""

    Title = Description = Credit = ReferenceURL = None

    def __init__(self, sp):
        self.sp = sp

    def to_wcs(self, target_shape):
        sp = self.sp
        frame = sp.get("CoordinateFrame") or "ICRS"
        if frame not in ("ICRS", "FK5", "FK4"):
            raise SystemExit(f"unsupported frame {frame}")
        proj = sp.get("CoordsystemProjection") or "TAN"
        if proj == "SIN":
            # WWT studies are TAN. Over < 1 deg the SIN/TAN difference is ~1e-5 of
            # the field (sub-pixel), so reinterpret rather than resample.
            fov = abs(sp["Scale"][0]) * sp["ReferenceDimension"][0]
            if fov > 1.0:
                raise SystemExit(f"SIN projection over {fov:.2f} deg: needs reprojection")
            print(f"note: treating SIN as TAN ({fov * 60:.1f}' field)")
            proj = "TAN"
        w = WCS(naxis=2)
        w.wcs.radesys = frame
        w.wcs.ctype = [f"RA---{proj}", f"DEC--{proj}"]
        w.wcs.crval = sp["ReferenceValue"][:2]
        w.wcs.crpix = sp["ReferencePixel"][:2]
        if sp.get("CDMatrix"):
            cd = sp["CDMatrix"]
            w.wcs.cd = [cd[0:2], cd[2:4]]
        else:
            w.wcs.cdelt = sp["Scale"][:2]
            rot = float(sp.get("Rotation") or 0.0)
            w.wcs.crota = [rot, rot]
        refw, refh = sp["ReferenceDimension"][:2]
        sx, sy = target_shape[0] / refw, target_shape[1] / refh
        if abs(sx - sy) / (sx + sy) >= 0.005:
            raise SystemExit("AVM aspect ratio does not match the image")
        if abs(sx - 1) > 1e-6:
            w.wcs.crpix = w.wcs.crpix * sx
            if w.wcs.has_cd():
                w.wcs.cd = w.wcs.cd / sx
            else:
                w.wcs.cdelt = w.wcs.cdelt / sx
        w.pixel_shape = target_shape
        return w


def main():
    feed, batch = sys.argv[1], sys.argv[2]
    for e in json.load(open(batch, encoding="utf-8")):
        uid = e["id"]
        outdir = os.path.join(feed, "processed", uid)
        os.makedirs(outdir, exist_ok=True)
        pil = Image.open(e["src"])
        pil.load()
        for k in ("xmp", "XML:com.adobe.xmp"):  # PIL can't re-save a tuple-typed XMP packet
            pil.info.pop(k, None)
        img = ImageLoader().load_pil(pil)
        if img.default_format is None:
            img._default_format = "jpg" if e["src"].lower().endswith((".jpg", ".jpeg")) else "png"
        pio = PyramidIO(outdir, default_format=img.default_format)
        b = Builder(pio)
        tiling = b.prepare_study_tiling(img)
        b.apply_avm_info(AVMShim(spatial(read_xmp(e["src"]))), img.width, img.height)
        b.make_thumbnail_from_other(img)
        b.execute_study_tiling(img, tiling)
        cascade_images(pio, b.imgset.tile_levels, averaging_merger)
        b.set_name(e["title"])
        im = b.imgset
        im.credits = e["credit"]
        im.credits_url = e["credits_url"]
        im.description = e["description"]
        b.place.description = e["description"]
        im.band_pass = Bandpass(e["band"])
        if e["band"] == "Multi":
            im.xmeta.bands = e["xbands"]
            im.xmeta.dominant_band = "Radio"
        b.write_index_rel_wtml()
        md = os.path.join(feed, "cache_done", uid)
        os.makedirs(md, exist_ok=True)
        with open(os.path.join(md, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump({"Title": e["title"], "Credit": e["credit"], "Description": e["description"],
                       "ReferenceURL": e["credits_url"], "Source": e["src_url"]}, f, indent=1, ensure_ascii=False)
        print(f"ok {uid}: {img.width}x{img.height} levels={im.tile_levels} "
              f"center=({im.center_x:.5f},{im.center_y:.5f}) rot={im.rotation_deg:.3f} "
              f"deg/tile={im.base_degrees_per_tile:.6g} {img.default_format}")


if __name__ == "__main__":
    main()
