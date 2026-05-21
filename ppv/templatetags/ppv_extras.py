from __future__ import annotations

import os

from django import template
import mimetypes
from io import BytesIO
from PIL import Image, UnidentifiedImageError

register = template.Library()


@register.filter
def media_kind(name: str | None) -> str:
    if not name:
        return "other"
    _root, ext = os.path.splitext(name.lower())
    # Try extension-based detection first
    if ext in {".mp4", ".webm", ".mov", ".m4v"}:
        return "video"
    if ext in {".mp3", ".wav", ".m4a", ".aac", ".ogg"}:
        return "audio"
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return "image"
    # Try mime-type guess from name
    mt, _ = mimetypes.guess_type(name)
    if mt:
        if mt.startswith("image/"):
            return "image"
        if mt.startswith("video/"):
            return "video"
        if mt.startswith("audio/"):
            return "audio"

    # As a last resort, if the storage gives no extension, attempt lightweight image header sniffing
    try:
        # The template filter receives only the name; attempt to open from default storage
        from django.core.files.storage import default_storage

        if default_storage.exists(name):
            with default_storage.open(name, "rb") as fh:
                data = fh.read(8192)
                try:
                    im = Image.open(BytesIO(data))
                    im.verify()
                    return "image"
                except (UnidentifiedImageError, OSError):
                    pass
    except Exception:
        pass

    return "other"

