"""Validation on real Roco Kingdom avatar screenshots.

Slices a screenshot grid of circular avatars into individual icons, builds a
database from one crop of each, then queries with differently cropped and
differently scaled crops of the same icons.

    python tests/test_real_icons.py [path/to/grid.png] --rows 3 --cols 6

Skips (exit 0) when no sample screenshot is available.
"""
from __future__ import annotations

import argparse
import random
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _eval import Stats
from iconmatch.database import IconDB

DEFAULT_SAMPLES = [
    (Path(__file__).resolve().parents[2] / "rocom_spirits" / "samples" / "sample_3x6.png", 3, 6),
]


def slice_grid(img: Image.Image, rows: int, cols: int) -> list[Image.Image]:
    w, h = img.size
    cw, ch = w / cols, h / rows
    return [img.crop((int(c * cw), int(r * ch), int((c + 1) * cw), int((r + 1) * ch)))
            for r in range(rows) for c in range(cols)]


def recrop(cell: Image.Image, rng: random.Random, keep_lo=0.72, keep_hi=1.0,
           scale_lo=0.45, scale_hi=1.4) -> Image.Image:
    """A different crop of the same cell, at a different resolution."""
    w, h = cell.size
    keep = rng.uniform(keep_lo, keep_hi)
    sw, sh = int(w * keep), int(h * keep)
    ox = (w - sw) // 2 + rng.randint(-int(w * 0.03), int(w * 0.03))
    oy = (h - sh) // 2 + rng.randint(-int(h * 0.03), int(h * 0.03))
    crop = cell.crop((max(0, ox), max(0, oy), min(w, ox + sw), min(h, oy + sh)))
    scale = rng.uniform(scale_lo, scale_hi)
    crop = crop.resize((max(24, int(crop.width * scale)), max(24, int(crop.height * scale))),
                       Image.LANCZOS)
    arr = np.asarray(crop.convert("RGB")).astype(np.int16) + rng.randint(-5, 5)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("grid", nargs="?", type=Path)
    ap.add_argument("--rows", type=int, default=3)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--queries", type=int, default=6)
    args = ap.parse_args(argv)

    if args.grid:
        samples = [(args.grid, args.rows, args.cols)]
    else:
        samples = [(p, r, c) for p, r, c in DEFAULT_SAMPLES if p.is_file()]
    if not samples:
        print("no sample screenshot available - skipping")
        return 0

    cells: list[Image.Image] = []
    for path, rows, cols in samples:
        print(f"using {path}  ({rows}x{cols})")
        cells += slice_grid(Image.open(path).convert("RGB"), rows, cols)
    n = len(cells)

    tmp = Path(tempfile.mkdtemp(prefix="iconmatch_real_"))
    try:
        db = IconDB.create(tmp, 1, "real")
        rng = random.Random(7)
        for i, cell in enumerate(cells):
            db.add(recrop(cell, rng, 0.86, 0.99), f"cell_{i:02d}")

        stats = Stats(db)
        for i, cell in enumerate(cells):
            for _ in range(args.queries):
                stats.add(db.search(recrop(cell, rng), top=n), f"cell_{i:02d}")

        print(f"icons               : {n}")
        ok = stats.report()
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
