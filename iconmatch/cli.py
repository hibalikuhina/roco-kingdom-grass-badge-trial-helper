"""Headless companion to the GUI: work with image files instead of the clipboard.

    python -m iconmatch.cli list
    python -m iconmatch.cli match --db 1 shot.png
    python -m iconmatch.cli add   --db 1 shot.png --name Pikachu
    python -m iconmatch.cli add   --db 1 folder/*.png --force
    python -m iconmatch.cli add   --db 1 grid_screenshot.png   # split automatically
    python -m iconmatch.cli remove --db 1 0003
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from . import imaging
from .database import DEFAULT_ROOT, IconDB, list_dbs


def _open_or_create(root: Path, db_id: int, create: bool) -> IconDB:
    db = IconDB(root, db_id)
    if db.exists:
        db.load()
        return db
    if not create:
        raise SystemExit(f"no database {db_id} under {root} (use --create)")
    return IconDB.create(root, db_id)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="iconmatch.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="database root folder")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list databases")

    p = sub.add_parser("match", help="match image files against a database")
    p.add_argument("--db", type=int, required=True)
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--top", type=int, default=3)

    p = sub.add_parser("add", help="add image files to a database")
    p.add_argument("--db", type=int, required=True)
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--name", default="", help="only meaningful with a single file")
    p.add_argument("--create", action="store_true", help="create the database if missing")
    p.add_argument("--force", action="store_true", help="add even if a similar icon exists")
    p.add_argument("--no-split", action="store_true",
                   help="treat each file as one icon instead of auto-splitting a grid")

    p = sub.add_parser("remove", help="remove an icon by id")
    p.add_argument("--db", type=int, required=True)
    p.add_argument("icon_id")

    args = ap.parse_args(argv)

    if args.cmd == "list":
        rows = list_dbs(args.root)
        if not rows:
            print(f"no databases under {args.root}")
        for db_id, count in rows:
            print(f"DB {db_id:03d}  {count} icon(s)")
        return 0

    if args.cmd == "match":
        db = _open_or_create(args.root, args.db, create=False)
        for f in args.files:
            found = db.search(Image.open(f), top=args.top)
            if not found.results:
                print(f"{f}: N (database is empty)")
                continue
            verdict = "Y" if db.is_match(found) else "N"
            extra = "  ".join(f"{i.id}:{s:.3f}" for i, s in found.results[1:])
            print(f"{f}: {verdict}  best={found.best.id} {found.best.name} "
                  f"sim={found.similarity:.3f} standout={found.confidence:.3f}   {extra}")
        return 0

    if args.cmd == "add":
        db = _open_or_create(args.root, args.db, create=args.create)
        for f in args.files:
            image = Image.open(f)
            crops = [] if args.no_split else imaging.split_grid(image)
            if crops:
                print(f"{f}: grid of {len(crops)} icons")
                pieces = [(c, f"{f.stem}_{i:02d}") for i, c in enumerate(crops)]
            else:
                pieces = [(image, args.name
                           if (args.name and len(args.files) == 1) else f.stem)]
            for piece, name in pieces:
                found = db.search(piece, top=1)
                if db.is_duplicate(found) and not args.force:
                    print(f"  {name}: SKIPPED - too similar to {found.best.id} "
                          f"{found.best.name} (sim={found.similarity:.3f} "
                          f"standout={found.confidence:.3f}); use --force to add anyway")
                    continue
                icon = db.add(piece, name, tile=found.tile)
                print(f"  {name}: added as {icon.id} {icon.name}")
        return 0

    if args.cmd == "remove":
        db = _open_or_create(args.root, args.db, create=False)
        db.remove(args.icon_id)
        print(f"removed {args.icon_id}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
