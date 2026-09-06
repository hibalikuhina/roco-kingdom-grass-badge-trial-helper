"""Grid splitting: one screenshot of many icons -> one crop per icon.

Covers a real screenshot, synthetic grids of several shapes (including a
partial last row and an uneven one), and the single-icon case that must fall
back to "not a grid".

    python tests/test_grid_split.py
"""
from __future__ import annotations

import random
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from iconmatch import config, imaging
from iconmatch.database import IconDB

REAL_GRID = Path(__file__).resolve().parents[2] / "rocom_spirits" / "samples" / "sample_3x6.png"
ART_DIR = Path(__file__).resolve().parents[2] / "rocom_spirits" / "data" / "icons"


def build_sheet(arts, rows: int, cols: int, count: int, cell: int = 190,
                jitter: int = 6) -> Image.Image:
    """A grid sheet like the game's, with per-cell jitter and a partial last row."""
    rng = random.Random(cols * 31 + rows)
    sheet = Image.new("RGB", (cols * cell, rows * cell), config.CANON_BG)
    placed = 0
    for r in range(rows):
        for c in range(cols):
            if placed >= count:
                return sheet
            art = arts[placed].convert("RGBA")
            box = art.getbbox()
            if box:
                art = art.crop(box)
            k = cell * rng.uniform(0.56, 0.68) / max(art.size)
            art = art.resize((max(1, int(art.width * k)), max(1, int(art.height * k))),
                             Image.LANCZOS)
            disc = Image.new("RGB", (cell, cell), config.CANON_BG)
            from PIL import ImageDraw
            ImageDraw.Draw(disc).ellipse((cell * .17, cell * .17, cell * .83, cell * .83),
                                         fill=(26, 24, 28))
            disc.paste(art, ((cell - art.width) // 2, (cell - art.height) // 2), art)
            sheet.paste(disc, (c * cell + rng.randint(-jitter, jitter),
                               r * cell + rng.randint(-jitter, jitter)))
            placed += 1
    return sheet


def main() -> int:
    failures = []

    # ---- real screenshot: split, store, and match every icon back
    if REAL_GRID.is_file():
        crops = imaging.split_grid(Image.open(REAL_GRID))
        print(f"real screenshot {REAL_GRID.name}: {len(crops)} icons (expected 18)")
        if len(crops) != 18:
            failures.append(f"real grid split gave {len(crops)}, expected 18")
        tmp = Path(tempfile.mkdtemp(prefix="iconmatch_grid_"))
        try:
            db = IconDB.create(tmp, 1, "grid")
            for i, crop in enumerate(crops):
                db.add(crop, f"cell_{i:02d}")
            hits = 0
            for i, crop in enumerate(crops):
                found = db.search(crop, top=1)
                hits += db.is_match(found) and found.best.name == f"cell_{i:02d}"
            print(f"  stored and matched back: {hits}/{len(crops)}")
            if hits != len(crops):
                failures.append(f"only {hits}/{len(crops)} split icons matched themselves")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        print(f"real screenshot not available ({REAL_GRID}) - skipped")

    # ---- synthetic sheets of assorted shapes
    files = sorted(ART_DIR.glob("*.png"))[:40] if ART_DIR.is_dir() else []
    if files:
        arts = [Image.open(f) for f in files]
        for rows, cols, count in ((2, 3, 6), (4, 7, 28), (5, 6, 30), (3, 5, 13), (1, 4, 4)):
            sheet = build_sheet(arts, rows, cols, count)
            got = len(imaging.split_grid(sheet))
            state = "ok" if got == count else "MISMATCH"
            print(f"synthetic {rows}x{cols} holding {count:2d} icons -> {got:2d}  {state}")
            if got != count:
                failures.append(f"{rows}x{cols}/{count} grid split gave {got}")

        # ---- a single icon is not a grid
        single = build_sheet(arts, 1, 1, 1)
        got = imaging.split_grid(single)
        print(f"single icon -> {len(got)} (expected 0, meaning 'not a grid')")
        if got:
            failures.append(f"single icon split into {len(got)}")
    else:
        print(f"artwork not available ({ART_DIR}) - synthetic sheets skipped")

    for f in failures:
        print("  FAIL:", f)
    print("RESULT:", "PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
