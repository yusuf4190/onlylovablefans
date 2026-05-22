from __future__ import annotations

import os
from io import BytesIO
from typing import Any

import mimetypes
from django import template
from PIL import Image, UnidentifiedImageError

register = template.Library()


@register.filter
def media_kind(value: Any) -> str:
    """
    Best-effort media kind detection for Content.media_file.

    Accepts either a file name (str) or a Django FieldFile-like object.
    """
    if not value:
        return "other"

    name = getattr(value, "name", value)
    if not isinstance(name, str) or not name:
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

    # As a last resort, if the storage gives no extension, attempt lightweight image header sniffing.
    # Prefer the file's own storage when available (PrivateFileField uses a non-default storage).
    try:
        storage = getattr(value, "storage", None)
        if storage and hasattr(storage, "open"):
            with storage.open(name, "rb") as fh:
                data = fh.read(8192)
        else:
            from django.core.files.storage import default_storage

            if not default_storage.exists(name):
                return "other"
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
