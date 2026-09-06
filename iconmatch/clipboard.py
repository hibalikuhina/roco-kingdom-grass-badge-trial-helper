"""Clipboard image input."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageGrab

from .i18n import t


class ClipboardError(RuntimeError):
    pass


def grab_image() -> Image.Image:
    """Return the clipboard image, or raise ClipboardError with a reason."""
    try:
        data = ImageGrab.grabclipboard()
    except Exception as exc:                      # pragma: no cover - OS specific
        raise ClipboardError(t("clip.read_failed", error=exc)) from exc

    if isinstance(data, Image.Image):
        return data
    if isinstance(data, list):                    # copied files rather than pixels
        for item in data:
            p = Path(str(item))
            try:
                img = Image.open(p)
                img.load()
                return img
            except Exception:
                continue
        raise ClipboardError(t("clip.files_no_image"))
    raise ClipboardError(t("clip.no_image"))
