"""Clipboard image input."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageGrab


class ClipboardError(RuntimeError):
    pass


def grab_image() -> Image.Image:
    """Return the clipboard image, or raise ClipboardError with a reason."""
    try:
        data = ImageGrab.grabclipboard()
    except Exception as exc:                      # pragma: no cover - OS specific
        raise ClipboardError(f"could not read the clipboard: {exc}") from exc

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
        raise ClipboardError("the clipboard holds files, but none of them is an image")
    raise ClipboardError("the clipboard does not contain an image")
