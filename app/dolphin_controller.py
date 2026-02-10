"""Controller for Dolphin Anty profiles on Windows."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class DolphinProfileSession:
    profile_id: str
    status: str
    connection: Optional[Dict]


def _api_request(method: str, url: str, payload: Optional[Dict] = None) -> Dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Dolphin API error: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Dolphin API error: {exc.reason}") from exc

    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError("Dolphin API returned invalid JSON") from exc


def start_profile(
    profile_id: str,
    *,
    base_url: str = "http://localhost:3001",
    wait_ready: bool = True,
    timeout_s: int = 60,
) -> DolphinProfileSession:
    """Start a Dolphin profile and return connection info for automation."""
    url = f"{base_url.rstrip('/')}/profile/start"
    response = _api_request("POST", url, {"profile_id": profile_id})
    connection = response.get("automation") or response.get("ws") or response

    session = DolphinProfileSession(
        profile_id=profile_id,
        status="STARTED",
        connection=connection if isinstance(connection, dict) else None,
    )

    if wait_ready:
        if not wait_for_healthcheck(profile_id, base_url=base_url, timeout_s=timeout_s):
            raise RuntimeError("Browser healthcheck failed after start")

    return session


def stop_profile(profile_id: str, *, base_url: str = "http://localhost:3001") -> None:
    """Stop a Dolphin profile."""
    url = f"{base_url.rstrip('/')}/profile/stop"
    _api_request("POST", url, {"profile_id": profile_id})


def healthcheck(profile_id: str, *, base_url: str = "http://localhost:3001") -> bool:
    """Return True if browser is alive for the profile."""
    url = f"{base_url.rstrip('/')}/profile/healthcheck"
    response = _api_request("POST", url, {"profile_id": profile_id})
    return bool(response.get("alive") or response.get("status") == "ok")


def wait_for_healthcheck(
    profile_id: str,
    *,
    base_url: str = "http://localhost:3001",
    timeout_s: int = 60,
    interval_s: float = 2.0,
) -> bool:
    """Wait until the profile reports healthy or timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if healthcheck(profile_id, base_url=base_url):
            return True
        time.sleep(interval_s)
    return False
