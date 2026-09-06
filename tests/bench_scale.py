"""How well does matching hold up with a few hundred icons in one database?

Renders the real Roco Kingdom creature artwork into avatar-style tiles (beige
background + black disc), stores one rendering of each, then queries with
independently cropped/scaled renderings.  This is the honest stress test for
the y/n threshold: unlike the 18-icon sample, it contains many near-duplicate
creatures (evolutions, recolours), which is where a fixed threshold hurts.

    python tests/bench_scale.py [--icons 200] [--queries 2]

Skips (exit 0) when the artwork folder is not available.
"""
from __future__ import annotations

import argparse
import random
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _eval import Stats
from iconmatch import config
from iconmatch.database import IconDB

ART_DIR = Path(__file__).resolve().parents[2] / "rocom_spirits" / "data" / "icons"
BG = config.CANON_BG


def make_avatar(art: Image.Image, rng: random.Random, size: int = 200) -> Image.Image:
    """Compose one artwork into a circular avatar on the game background."""
    canvas = Image.new("RGB", (size, size), BG)
    ImageDraw.Draw(canvas).ellipse(
        (size * 0.12, size * 0.12, size * 0.88, size * 0.88), fill=(26, 24, 28))
    art = art.convert("RGBA")
    bbox = art.getbbox()
    if bbox:
        art = art.crop(bbox)
    target = size * rng.uniform(0.72, 0.86)
    k = target / max(art.size)
    art = art.resize((max(1, int(art.width * k)), max(1, int(art.height * k))), Image.LANCZOS)
    canvas.paste(art, ((size - art.width) // 2, (size - art.height) // 2), art)
    return canvas


def recrop(avatar: Image.Image, rng: random.Random) -> Image.Image:
    w, h = avatar.size
    keep = rng.uniform(0.74, 1.0)
    sw = int(w * keep)
    ox = (w - sw) // 2 + rng.randint(-int(w * 0.03), int(w * 0.03))
    oy = (h - sw) // 2 + rng.randint(-int(h * 0.03), int(h * 0.03))
    crop = avatar.crop((max(0, ox), max(0, oy), min(w, ox + sw), min(h, oy + sw)))
    px = rng.randrange(60, 260)
    crop = crop.resize((px, px), Image.LANCZOS)
    arr = np.asarray(crop).astype(np.int16) + rng.randint(-5, 5)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", type=Path, default=ART_DIR)
    ap.add_argument("--icons", type=int, default=250)
    ap.add_argument("--queries", type=int, default=2)
    args = ap.parse_args(argv)

    files = sorted(args.art.glob("*.png")) if args.art.is_dir() else []
    if not files:
        print(f"no artwork under {args.art} - skipping")
        return 0
    rng = random.Random(11)
    files = files[:args.icons]
    print(f"building {len(files)} avatars from {args.art}")

    tmp = Path(tempfile.mkdtemp(prefix="iconmatch_bench_"))
    try:
        db = IconDB.create(tmp, 1, "bench")
        avatars = []
        for i, f in enumerate(files):
            av = make_avatar(Image.open(f), rng)
            avatars.append(av)
            db.add(recrop(av, rng), f.stem)

        stats = Stats(db)
        for i, av in enumerate(avatars):
            for _ in range(args.queries):
                stats.add(db.search(recrop(av, rng), top=len(files)), files[i].stem)

        print(f"icons               : {len(files)}")
        stats.report()
        print("(this set contains genuine near-duplicates - evolutions and "
              "recolours of the same creature - so some 'said N when absent' "
              "failures are expected and are exactly the cases the add dialog "
              "shows you.)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
