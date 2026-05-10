from __future__ import annotations

import os

from django import template

register = template.Library()


@register.filter
def media_kind(name: str | None) -> str:
    if not name:
        return "other"
    _root, ext = os.path.splitext(name.lower())
    if ext in {".mp4", ".webm", ".mov", ".m4v"}:
        return "video"
    if ext in {".mp3", ".wav", ".m4a", ".aac", ".ogg"}:
        return "audio"
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return "image"
    return "other"

