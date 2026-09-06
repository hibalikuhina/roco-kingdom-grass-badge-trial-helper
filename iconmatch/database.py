"""On-disk icon databases.

Layout::

    data/db_001/index.json      metadata + thresholds
    data/db_001/norm/0001.png   normalised RGBA tile (what matching uses)
    data/db_001/raw/0001.png    the image the user pasted, untouched
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from . import config, features, imaging
from .i18n import t

def _default_root() -> Path:
    """Where the db_XXX folders live.

    A PyInstaller one-file build unpacks itself into a temp directory that is
    wiped on exit, so ``__file__`` is the one place the databases must *not*
    go: they belong next to the exe the user actually keeps.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    return Path(__file__).resolve().parent.parent / "data"


DEFAULT_ROOT = _default_root()
_DB_DIR_RE = re.compile(r"^db_(\d+)$")


@dataclass
class Icon:
    id: str
    name: str
    added: str
    tile: Image.Image = field(repr=False)
    vec: np.ndarray = field(repr=False)
    raw_path: Path | None = None

    @property
    def label(self) -> str:
        return f"{self.id}  {self.name}"


@dataclass
class SearchResult:
    """Outcome of one query, with everything the verdict needs."""
    tile: Image.Image                    # normalised query tile
    results: list[tuple[Icon, float]]    # best first
    median: float                        # median similarity over the whole DB
    db_size: int

    @property
    def best(self) -> Icon | None:
        return self.results[0][0] if self.results else None

    @property
    def similarity(self) -> float:
        """Raw descriptor score of the best candidate."""
        return self.results[0][1] if self.results else 0.0

    @property
    def confidence(self) -> float:
        """How far the best candidate stands out above the rest of the DB.

        Scale free, which the raw similarity is not: a database of icons that
        all share the same dark disc pushes every similarity upwards at once,
        and this ratio cancels that out.
        """
        if self.db_size < config.MIN_ICONS_FOR_REL or not self.results:
            return 1.0 if self.results else 0.0
        return max(0.0, (self.similarity - self.median) / max(1e-6, 1.0 - self.median))

    def is_match(self, sim_thr: float, rel_thr: float) -> bool:
        return bool(self.results) and self.similarity >= sim_thr and self.confidence >= rel_thr


def list_dbs(root: Path = DEFAULT_ROOT) -> list[tuple[int, int]]:
    """[(db_id, icon_count), ...] sorted by id."""
    root = Path(root)
    out = []
    if root.is_dir():
        for p in sorted(root.iterdir()):
            m = _DB_DIR_RE.match(p.name)
            if p.is_dir() and m:
                try:
                    meta = json.loads((p / "index.json").read_text("utf-8"))
                    out.append((int(m.group(1)), len(meta.get("icons", []))))
                except (OSError, ValueError):
                    out.append((int(m.group(1)), 0))
    return sorted(out)


class IconDB:
    THRESHOLD_KEYS = {"match_sim": config.MATCH_SIM, "match_rel": config.MATCH_REL,
                      "dup_sim": config.DUP_SIM, "dup_rel": config.DUP_REL}

    def __init__(self, root: Path, db_id: int):
        self.root = Path(root)
        self.id = int(db_id)
        self.dir = self.root / f"db_{self.id:03d}"
        self.norm_dir = self.dir / "norm"
        self.raw_dir = self.dir / "raw"
        self.icons: list[Icon] = []
        self.meta: dict = {}
        self._matrix = np.zeros((0, 1), dtype=np.float32)

    # ------------------------------------------------------------ lifecycle
    @property
    def exists(self) -> bool:
        return (self.dir / "index.json").is_file()

    @classmethod
    def create(cls, root: Path, db_id: int, name: str = "") -> "IconDB":
        db = cls(root, db_id)
        if db.exists:
            raise FileExistsError(t("db.exists", id=db_id, path=db.dir))
        db.norm_dir.mkdir(parents=True, exist_ok=True)
        db.raw_dir.mkdir(parents=True, exist_ok=True)
        db.meta = {
            "id": db.id,
            "name": name or f"db_{db.id:03d}",
            "created": datetime.now().isoformat(timespec="seconds"),
            "descriptor_version": config.DESCRIPTOR_VERSION,
            **cls.THRESHOLD_KEYS,
            "icons": [],
        }
        db._save_meta()
        return db

    @classmethod
    def open(cls, root: Path, db_id: int) -> "IconDB":
        db = cls(root, db_id)
        if not db.exists:
            raise FileNotFoundError(t("db.not_found", id=db_id, root=db.root))
        db.load()
        return db

    def load(self) -> None:
        self.meta = json.loads((self.dir / "index.json").read_text("utf-8"))
        self.icons = []
        for rec in self.meta.get("icons", []):
            tile_path = self.dir / rec["norm"]
            if not tile_path.is_file():
                continue
            tile = Image.open(tile_path).convert("RGBA")
            tile.load()
            raw = self.dir / rec["raw"] if rec.get("raw") else None
            self.icons.append(Icon(
                id=rec["id"], name=rec.get("name", rec["id"]),
                added=rec.get("added", ""), tile=tile,
                vec=features.describe(tile),
                raw_path=raw if raw and raw.is_file() else None,
            ))
        self._rebuild_matrix()

    def _rebuild_matrix(self) -> None:
        self._matrix = (np.stack([i.vec for i in self.icons])
                        if self.icons else np.zeros((0, 1), dtype=np.float32))

    def _save_meta(self) -> None:
        self.meta["icons"] = [
            {"id": i.id, "name": i.name, "added": i.added,
             "norm": f"norm/{i.id}.png",
             "raw": f"raw/{i.id}.png" if i.raw_path else ""}
            for i in self.icons
        ]
        (self.dir / "index.json").write_text(
            json.dumps(self.meta, indent=2, ensure_ascii=False), "utf-8")

    # ------------------------------------------------------------ settings
    def threshold(self, key: str) -> float:
        return float(self.meta.get(key, self.THRESHOLD_KEYS[key]))

    def set_thresholds(self, **values: float) -> None:
        for key, value in values.items():
            if key not in self.THRESHOLD_KEYS:
                raise KeyError(key)
            self.meta[key] = round(float(value), 3)
        self._save_meta()

    def is_match(self, result: SearchResult) -> bool:
        return result.is_match(self.threshold("match_sim"), self.threshold("match_rel"))

    def is_duplicate(self, result: SearchResult) -> bool:
        return result.is_match(self.threshold("dup_sim"), self.threshold("dup_rel"))

    # ------------------------------------------------------------ querying
    def search(self, image: Image.Image, top: int = 5) -> SearchResult:
        return self.search_tile(imaging.normalize(image), top)

    def search_tile(self, tile: Image.Image, top: int = 5) -> SearchResult:
        if not self.icons:
            return SearchResult(tile, [], 0.0, 0)
        scores = features.score_matrix(features.describe_query(tile), self._matrix)
        order = np.argsort(-scores)
        # the median excludes the best candidate itself, so a two-icon database
        # cannot make its only rival look like the norm
        median = float(np.median(scores[order[1:]])) if len(scores) > 1 else 0.0
        return SearchResult(
            tile=tile,
            results=[(self.icons[i], float(scores[i])) for i in order[:top]],
            median=median,
            db_size=len(self.icons),
        )

    # ------------------------------------------------------------ mutation
    def _next_id(self) -> str:
        used = {i.id for i in self.icons}
        n = len(used) + 1
        while f"{n:04d}" in used:
            n += 1
        return f"{n:04d}"

    def add(self, image: Image.Image, name: str = "", tile: Image.Image | None = None) -> Icon:
        tile = tile if tile is not None else imaging.normalize(image)
        icon_id = self._next_id()
        self.norm_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        tile.save(self.norm_dir / f"{icon_id}.png")
        raw_path = self.raw_dir / f"{icon_id}.png"
        imaging.to_rgb(image).save(raw_path)
        icon = Icon(id=icon_id, name=name or icon_id,
                    added=datetime.now().isoformat(timespec="seconds"),
                    tile=tile, vec=features.describe(tile), raw_path=raw_path)
        self.icons.append(icon)
        self._rebuild_matrix()
        self._save_meta()
        return icon

    def replace(self, icon_id: str, image: Image.Image, name: str | None = None,
                tile: Image.Image | None = None) -> Icon:
        """Overwrite the images of an existing entry, keeping its id."""
        icon = self.get(icon_id)
        if icon is None:
            raise KeyError(icon_id)
        tile = tile if tile is not None else imaging.normalize(image)
        tile.save(self.norm_dir / f"{icon_id}.png")
        raw_path = self.raw_dir / f"{icon_id}.png"
        imaging.to_rgb(image).save(raw_path)
        icon.tile, icon.vec, icon.raw_path = tile, features.describe(tile), raw_path
        icon.added = datetime.now().isoformat(timespec="seconds")
        if name:
            icon.name = name
        self._rebuild_matrix()
        self._save_meta()
        return icon

    def rename(self, icon_id: str, name: str) -> None:
        icon = self.get(icon_id)
        if icon is not None:
            icon.name = name
            self._save_meta()

    def remove(self, icon_id: str) -> None:
        icon = self.get(icon_id)
        if icon is None:
            return
        self.icons.remove(icon)
        for p in (self.norm_dir / f"{icon_id}.png", self.raw_dir / f"{icon_id}.png"):
            if p.is_file():
                p.unlink()
        self._rebuild_matrix()
        self._save_meta()

    def get(self, icon_id: str) -> Icon | None:
        return next((i for i in self.icons if i.id == icon_id), None)

    def destroy(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)
