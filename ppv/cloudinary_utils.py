from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class CloudinaryConfig:
    cloud_name: str
    api_key: str
    api_secret: str


def get_cloudinary_config() -> CloudinaryConfig | None:
    cloudinary_url = (os.environ.get("CLOUDINARY_URL") or "").strip()
    cloud_name = (os.environ.get("CLOUDINARY_CLOUD_NAME") or "").strip()
    api_key = (os.environ.get("CLOUDINARY_API_KEY") or "").strip()
    api_secret = (os.environ.get("CLOUDINARY_API_SECRET") or "").strip()

    if cloudinary_url and not (cloud_name and api_key and api_secret):
        parsed = urlsplit(cloudinary_url)
        if parsed.scheme and parsed.username and parsed.password and parsed.hostname:
            api_key = api_key or parsed.username
            api_secret = api_secret or parsed.password
            cloud_name = cloud_name or parsed.hostname

    if not (cloud_name and api_key and api_secret):
        return None
    return CloudinaryConfig(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)


def cloudinary_enabled() -> bool:
    return get_cloudinary_config() is not None


def build_upload_signature(params: dict[str, str]) -> str:
    config = get_cloudinary_config()
    if not config:
        raise RuntimeError("Cloudinary is not configured.")

    pairs = [f"{key}={value}" for key, value in sorted(params.items()) if value not in {None, ""}]
    payload = "&".join(pairs) + config.api_secret
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def build_delivery_signature(path_to_sign: str) -> str:
    config = get_cloudinary_config()
    if not config:
        raise RuntimeError("Cloudinary is not configured.")

    digest = hashlib.sha1((path_to_sign + config.api_secret).encode("utf-8")).digest()
    token = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")[:8]
    return f"s--{token}--"


def build_cloudinary_url(
    public_id: str,
    *,
    resource_type: str = "image",
    delivery_type: str = "upload",
    format: str = "",
    sign: bool = False,
) -> str | None:
    config = get_cloudinary_config()
    if not config or not public_id:
        return None

    public_id = public_id.lstrip("/")
    suffix = f".{format.lstrip('.')}" if format else ""
    path_to_deliver = f"{public_id}{suffix}"

    if sign and delivery_type in {"authenticated", "private"}:
        signature = build_delivery_signature(path_to_deliver)
        return (
            f"https://res.cloudinary.com/{config.cloud_name}/"
            f"{resource_type}/{delivery_type}/{signature}/{path_to_deliver}"
        )

    return f"https://res.cloudinary.com/{config.cloud_name}/{resource_type}/{delivery_type}/{path_to_deliver}"
