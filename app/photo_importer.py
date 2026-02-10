"""Photo import module for downloading and validating batch photos."""

from __future__ import annotations

import imghdr
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PhotoImportResult:
    batch_id: str
    status: str
    photo_files: List[str]
    photo_urls: List[str]


def _api_get_json(url: str, token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"API request failed: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API request failed: {exc.reason}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("API returned invalid JSON") from exc


def fetch_batch(batch_id: str, api_base_url: str, token: str) -> dict:
    url = f"{api_base_url.rstrip('/')}/batches/{batch_id}"
    return _api_get_json(url, token)


def _sorted_photos(batch: dict) -> List[dict]:
    photos = batch.get("photos", [])
    if not isinstance(photos, list):
        raise ValueError("Batch photos must be a list")

    for photo in photos:
        if "index" not in photo or "url" not in photo:
            raise ValueError("Each photo must include index and url")

    indices = [photo["index"] for photo in photos]
    if len(indices) != len(set(indices)):
        raise ValueError("Photo indices must be unique")

    if sorted(indices) != list(range(1, len(indices) + 1)):
        raise ValueError("Photo indices must be consecutive starting from 1")

    return sorted(photos, key=lambda item: item["index"])


def _download_file(url: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Failed to download photo: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download photo: {exc.reason}") from exc

    with open(output_path, "wb") as file:
        file.write(data)


def _validate_photo(path: str) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Photo file missing: {path}")
    if os.path.getsize(path) == 0:
        raise ValueError(f"Photo file is empty: {path}")
    if imghdr.what(path) is None:
        raise ValueError(f"Photo file is not a valid image: {path}")


def import_photos(
    batch_id: str,
    api_base_url: str,
    token: str,
    output_dir: str,
) -> PhotoImportResult:
    """Download, validate, and order photos for a batch.

    Returns a PhotoImportResult with status set to PHOTOS_READY when successful.
    """
    batch = fetch_batch(batch_id, api_base_url, token)
    if batch.get("status") != "ready":
        raise RuntimeError(f"Batch {batch_id} is not ready")

    photos = _sorted_photos(batch)
    photo_files: List[str] = []
    photo_urls: List[str] = []

    for photo in photos:
        url = photo["url"]
        index = photo["index"]
        extension = os.path.splitext(url)[1] or ".jpg"
        filename = f"{index:02d}_{photo.get('type', 'photo')}{extension}"
        path = os.path.join(output_dir, batch_id, filename)
        _download_file(url, path)
        _validate_photo(path)
        photo_files.append(path)
        photo_urls.append(url)

    return PhotoImportResult(
        batch_id=batch_id,
        status="PHOTOS_READY",
        photo_files=photo_files,
        photo_urls=photo_urls,
    )
