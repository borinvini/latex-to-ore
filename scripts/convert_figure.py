#!/usr/bin/env python
"""Convert ONE figure to an ORE-compliant raster: TIFF or JPEG at print DPI.

Usage:  convert_figure.py <src> <dst_stem> <jpeg|tiff>
Writes <dst_stem>.jpg or <dst_stem>.tif.

ORE rule: 300 dpi for colour, 600 dpi for greyscale (auto-detected).
- Vector sources (.pdf/.eps): rasterized with poppler `pdftocairo` at the
  chosen dpi, then finalized with Pillow.
- Raster sources (.png/.jpg/.tif/...): opened directly with Pillow; dpi is
  written as metadata (a raster cannot be re-sampled to a higher true dpi).
Requires: Pillow; and, for vector sources, poppler `pdftocairo` on PATH.
Exit codes: 0 ok; 2 missing dependency; 3 conversion error.
"""
import os
import subprocess
import sys
import tempfile

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("ERROR: Pillow (PIL) not installed. `pip install Pillow`.\n")
    sys.exit(2)


def have(cmd):
    from shutil import which
    return which(cmd) is not None


def rasterize_vector(src, dpi, tmpdir):
    """PDF/EPS -> PNG at dpi using pdftocairo; return the PNG path."""
    if not have("pdftocairo"):
        sys.stderr.write("ERROR: pdftocairo (poppler) not found; needed for "
                         "vector sources. Install poppler or choose keep-as-is.\n")
        sys.exit(2)
    out = os.path.join(tmpdir, "page")
    subprocess.run(["pdftocairo", "-png", "-r", str(dpi), "-singlefile", src, out],
                   check=True)
    return out + ".png"


def is_greyscale(im):
    if im.mode in ("1", "L", "LA"):
        return True
    rgb = im.convert("RGB")
    small = rgb.resize((48, 48))
    return all(r == g == b for r, g, b in small.getdata())


def main():
    if len(sys.argv) != 4:
        sys.stderr.write(__doc__)
        sys.exit(3)
    src, dst_stem, fmt = sys.argv[1], sys.argv[2], sys.argv[3].lower()
    fmt = "TIFF" if fmt in ("tif", "tiff") else "JPEG"
    ext = ".tif" if fmt == "TIFF" else ".jpg"
    if not os.path.isfile(src):
        sys.stderr.write("ERROR: source not found: %s\n" % src)
        sys.exit(3)
    src_ext = os.path.splitext(src)[1].lower()
    is_vector = src_ext in (".pdf", ".eps")
    tmp = tempfile.mkdtemp()
    try:
        if is_vector:
            # Probe at low dpi to decide colour vs grey, then render at final dpi.
            probe = rasterize_vector(src, 72, tmp)
            grey = is_greyscale(Image.open(probe))
            dpi = 600 if grey else 300
            raster = rasterize_vector(src, dpi, tmp)
            im = Image.open(raster)
        else:
            im = Image.open(src)
            grey = is_greyscale(im)
            dpi = 600 if grey else 300
        im = im.convert("L" if grey else "RGB")
        dst = dst_stem + ext
        save_kw = {"dpi": (dpi, dpi)}
        if fmt == "JPEG":
            save_kw["quality"] = 95
        else:
            save_kw["compression"] = "tiff_lzw"
        im.save(dst, fmt, **save_kw)
        print("%s -> %s (%s, %s, %ddpi)"
              % (os.path.basename(src), os.path.basename(dst),
                 "greyscale" if grey else "colour", "%dx%d" % im.size, dpi))
    except subprocess.CalledProcessError as e:
        sys.stderr.write("ERROR: rasterization failed: %s\n" % e)
        sys.exit(3)
    except Exception as e:  # noqa
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(3)


if __name__ == "__main__":
    main()
