"""Descriptors and similarity for normalised icon tiles.

Every descriptor is a single float32 vector built from four L2-normalised
blocks (colour layout / colour histogram / DCT hash / silhouette) pre-scaled
by their weights, so a plain dot product yields the final 0..1 score and a
whole database can be scored with one matrix multiply.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from . import config

GRID = 28          # colour-layout grid  (28*28*3 = 2352 dims)
HASH_IMG = 32      # image size fed to the DCT hash
HASH_BITS = 8      # top-left 8x8 DCT coefficients
SHAPE = 16         # silhouette grid

HIST_H, HIST_S, HIST_V = 12, 4, 4

# score = dot(q, d) + HASH_OFFSET   (the hash block contributes (dot+1)/2)
HASH_OFFSET = config.W_HASH / 2.0


def _l2(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-8 else v


_DCT = None


def _dct_matrix(n: int) -> np.ndarray:
    global _DCT
    if _DCT is None or _DCT.shape[0] != n:
        k = np.arange(n)
        _DCT = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
        _DCT[0] *= 1 / np.sqrt(2)
    return _DCT


def _grid_block(tile: Image.Image) -> np.ndarray:
    a = np.asarray(tile.convert("RGB").resize((GRID, GRID), Image.BILINEAR), dtype=np.float32) / 255.0
    v = a.reshape(-1)
    return _l2(v - v.mean())


def _hist_block(tile: Image.Image) -> np.ndarray:
    hsv = np.asarray(tile.convert("RGB").convert("HSV"), dtype=np.float32)
    alpha = np.asarray(tile.split()[-1], dtype=np.float32) / 255.0
    sel = alpha > 0.5
    if sel.sum() < 16:                       # degenerate tile
        return _l2(np.ones(HIST_H * HIST_S * HIST_V, dtype=np.float32))
    h = (hsv[..., 0][sel] / 256.0 * HIST_H).astype(np.int32).clip(0, HIST_H - 1)
    s = (hsv[..., 1][sel] / 256.0 * HIST_S).astype(np.int32).clip(0, HIST_S - 1)
    v = (hsv[..., 2][sel] / 256.0 * HIST_V).astype(np.int32).clip(0, HIST_V - 1)
    idx = (h * HIST_S + s) * HIST_V + v
    hist = np.bincount(idx, minlength=HIST_H * HIST_S * HIST_V).astype(np.float32)
    hist /= hist.sum()
    return _l2(np.sqrt(hist))                # Hellinger: dot == Bhattacharyya


def _hash_block(tile: Image.Image) -> np.ndarray:
    g = np.asarray(tile.convert("L").resize((HASH_IMG, HASH_IMG), Image.BILINEAR), dtype=np.float32)
    d = _dct_matrix(HASH_IMG)
    coef = d @ g @ d.T
    low = coef[:HASH_BITS, :HASH_BITS].reshape(-1)[1:]     # drop DC
    bits = np.where(low > np.median(low), 1.0, -1.0).astype(np.float32)
    return _l2(bits)                                        # dot in [-1, 1]


def _shape_block(tile: Image.Image) -> np.ndarray:
    a = np.asarray(tile.split()[-1].resize((SHAPE, SHAPE), Image.BILINEAR), dtype=np.float32) / 255.0
    return _l2(a.reshape(-1))


def describe(tile: Image.Image) -> np.ndarray:
    """Normalised RGBA tile -> weighted descriptor vector.

    The tile is softened first: upscaling a 60px screenshot to 128px yields a
    much blurrier tile than a 220px one, and matching that difference is worth
    more than the high-frequency detail it costs.
    """
    if config.DESC_BLUR:
        tile = tile.filter(ImageFilter.GaussianBlur(config.DESC_BLUR))
    # sqrt(weight) on both sides so that dot(a, b) contributes weight * cosine
    return np.concatenate([
        _grid_block(tile) * np.sqrt(config.W_GRID),
        _hist_block(tile) * np.sqrt(config.W_HIST),
        _hash_block(tile) * np.sqrt(config.W_HASH / 2.0),
        _shape_block(tile) * np.sqrt(config.W_SHAPE),
    ]).astype(np.float32)


# ---------------------------------------------------------------- variants
SCALES = (0.93, 1.0, 1.07)
SHIFTS = (-4, 0, 4)          # pixels, in NORM_SIZE space


def _transform(tile: Image.Image, scale: float, dx: int, dy: int) -> Image.Image:
    size = tile.size[0]
    if abs(scale - 1.0) > 1e-6:
        s = max(8, int(round(size * scale)))
        z = tile.resize((s, s), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), config.CANON_BG + (0,))
        canvas.paste(z, ((size - s) // 2, (size - s) // 2))
        tile = canvas
    if dx or dy:
        canvas = Image.new("RGBA", (size, size), config.CANON_BG + (0,))
        canvas.paste(tile, (dx, dy))
        tile = canvas
    return tile


def describe_query(tile: Image.Image) -> np.ndarray:
    """Descriptors for a small family of scale/translation variants (N x D).

    Makes matching tolerant of how tightly the user cropped the screenshot.
    """
    rows = []
    for sc in SCALES:
        for dx in SHIFTS:
            for dy in SHIFTS:
                rows.append(describe(_transform(tile, sc, dx, dy)))
    return np.stack(rows)


def score_matrix(query: np.ndarray, db: np.ndarray) -> np.ndarray:
    """query (N x D) vs db (M x D) -> best score per db entry (M,), 0..1."""
    if db.size == 0:
        return np.zeros(0, dtype=np.float32)
    if query.ndim == 1:
        query = query[None, :]
    s = query @ db.T + HASH_OFFSET
    return np.clip(s.max(axis=0), 0.0, 1.0)
