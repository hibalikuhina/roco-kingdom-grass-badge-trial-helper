"""Synthetic end-to-end check of normalisation + matching + the DB layer.

Builds a set of fake game icons (beige background, black round frame, a body
that pokes outside the frame), stores one rendering of each in a database,
then queries with differently cropped / differently sized / noisier renderings
of the same icons.

    python tests/test_pipeline.py
"""
from __future__ import annotations

import random
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _eval import Stats
from iconmatch.database import IconDB

BG = (236, 230, 214)


def make_icon(seed: int, size: int = 220) -> Image.Image:
    """A distinctive fake icon rendered on a canvas roughly 1.6x its own size."""
    rng = random.Random(seed)
    canvas = int(size * 1.6)
    img = Image.new("RGB", (canvas, canvas), BG)
    d = ImageDraw.Draw(img)
    cx = cy = canvas // 2
    r = size // 2

    body = tuple(rng.randrange(40, 240) for _ in range(3))
    accent = tuple(rng.randrange(40, 240) for _ in range(3))

    # black round frame
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(24, 24, 26))

    # ears / horns that stick out of the frame
    for k in range(rng.choice((2, 3))):
        ang = -2.4 + k * 1.2 + rng.uniform(-0.3, 0.3)
        ex = cx + int(np.cos(ang) * r * 0.95)
        ey = cy + int(np.sin(ang) * r * 0.95)
        er = int(r * rng.uniform(0.22, 0.4))
        d.ellipse((ex - er, ey - er, ex + er, ey + er), fill=accent)

    # body
    br = int(r * rng.uniform(0.55, 0.78))
    shape = rng.choice(("ellipse", "rounded", "diamond"))
    if shape == "ellipse":
        d.ellipse((cx - br, cy - br, cx + br, cy + br), fill=body)
    elif shape == "rounded":
        d.rounded_rectangle((cx - br, cy - br, cx + br, cy + br), radius=br // 3, fill=body)
    else:
        d.polygon([(cx, cy - br), (cx + br, cy), (cx, cy + br), (cx - br, cy)], fill=body)

    # eyes + mouth
    eo = int(br * 0.38)
    er = max(3, int(br * rng.uniform(0.13, 0.2)))
    for sx in (-1, 1):
        d.ellipse((cx + sx * eo - er, cy - er - er // 2, cx + sx * eo + er, cy + er - er // 2),
                  fill=(250, 250, 250))
        d.ellipse((cx + sx * eo - er // 2, cy - er // 2 - er // 2,
                   cx + sx * eo + er // 2, cy + er // 2 - er // 2), fill=(20, 20, 20))
    mw = int(br * 0.4)
    d.arc((cx - mw, cy + br // 6, cx + mw, cy + br // 2), 20, 160, fill=(20, 20, 20), width=3)
    return img


def render_query(seed: int, rng: random.Random) -> Image.Image:
    """Same icon, but cropped and scaled the way a user's screenshot would be."""
    img = make_icon(seed)
    w, h = img.size
    keep = rng.uniform(0.75, 1.0)           # how much of the canvas the crop keeps
    side = int(min(w, h) * keep)
    ox = (w - side) // 2 + rng.randint(-6, 6)
    oy = (h - side) // 2 + rng.randint(-6, 6)
    crop = img.crop((max(0, ox), max(0, oy), max(0, ox) + side, max(0, oy) + side))

    target = rng.randrange(48, 240)
    crop = crop.resize((target, target), Image.LANCZOS)

    arr = np.asarray(crop).astype(np.int16)
    arr += rng.randint(-4, 4)                                     # background/lighting drift
    arr += np.random.default_rng(seed).integers(-3, 4, arr.shape)  # texture noise
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def main() -> int:
    n_icons, n_queries = 14, 4
    tmp = Path(tempfile.mkdtemp(prefix="iconmatch_test_"))
    try:
        db = IconDB.create(tmp, 1, "synthetic")
        for s in range(n_icons):
            db.add(make_icon(s), f"icon_{s:02d}")
        assert len(db.icons) == n_icons

        rng = random.Random(1234)
        stats = Stats(db)
        for s_i in range(n_icons):
            for _ in range(n_queries):
                found = db.search(render_query(s_i, rng), top=n_icons)
                stats.add(found, f"icon_{s_i:02d}")

        # persistence round-trip
        reopened = IconDB.open(tmp, 1)
        assert len(reopened.icons) == n_icons
        found = reopened.search(render_query(3, rng), top=1)
        assert found.best.name == "icon_03", found.results
        assert reopened.is_match(found)

        # unrelated image must not be claimed as a match
        noise = Image.fromarray(
            np.random.default_rng(0).integers(0, 255, (160, 160, 3), dtype=np.uint8), "RGB")
        noise_found = reopened.search(noise, top=1)
        noise_score = noise_found.similarity
        assert not reopened.is_match(noise_found)

        db.remove(db.icons[0].id)
        assert len(IconDB.open(tmp, 1).icons) == n_icons - 1

        ok = stats.report()
        print(f"random-noise query  : similarity {noise_score:.3f}")
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
