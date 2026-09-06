"""Shared evaluation helpers for the three test scripts.

Every test asks the same two questions of each query:

* the icon *is* in the database  -> the app must say Y
* the icon is *not* in the database (drop it and rescore) -> the app must say N
"""
from __future__ import annotations

import numpy as np

from iconmatch.database import SearchResult


def without(found: SearchResult, name: str) -> SearchResult:
    """The same query as if the icon called `name` had never been added."""
    rest = [(icon, score) for icon, score in found.results if icon.name != name]
    scores = [s for _, s in rest]
    median = float(np.median(scores[1:])) if len(scores) > 1 else 0.0
    return SearchResult(found.tile, rest, median, found.db_size - 1)


class Stats:
    """Collects verdicts and prints a report."""

    def __init__(self, db):
        self.db = db
        self.rows: list[tuple[bool, float, float, bool, float, float]] = []
        self.rank_hits = 0

    def add(self, found: SearchResult, name: str) -> None:
        absent = without(found, name)
        self.rank_hits += bool(found.best) and found.best.name == name
        self.rows.append((self.db.is_match(found), found.similarity, found.confidence,
                          self.db.is_match(absent), absent.similarity, absent.confidence))

    def report(self, label: str = "") -> bool:
        a = np.array(self.rows, dtype=float)
        n = len(a)
        yes_ok, no_ok = a[:, 0].sum(), n - a[:, 3].sum()
        head = f"{label} " if label else ""
        print(f"{head}queries              : {n}")
        print(f"{head}correct top-1 ranking: {self.rank_hits}/{n}")
        print(f"{head}said Y when present  : {int(yes_ok)}/{n}   "
              f"[sim min {a[:, 1].min():.3f} mean {a[:, 1].mean():.3f}] "
              f"[stand-out min {a[:, 2].min():.3f} mean {a[:, 2].mean():.3f}]")
        print(f"{head}said N when absent   : {int(no_ok)}/{n}   "
              f"[sim max {a[:, 4].max():.3f} mean {a[:, 4].mean():.3f}] "
              f"[stand-out max {a[:, 5].max():.3f} mean {a[:, 5].mean():.3f}]")
        return bool(yes_ok == n and no_ok == n and self.rank_hits == n)
