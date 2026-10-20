from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


class APIRequestError(RuntimeError):
    """HTTP/API failure with stable machine-readable fields when available."""

    def __init__(self, status: int, code: str, message: str, *, details: Any = None,
                 request_id: str | None = None):
        self.status = status
        self.code = code
        self.details = details
        self.request_id = request_id
        suffix = f" (request_id={request_id})" if request_id else ""
        super().__init__(f"HTTP {status} {code}: {message}{suffix}")


def api_error_from_http(exc: urllib.error.HTTPError, text: str) -> APIRequestError:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = {}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    return APIRequestError(
        exc.code,
        str(error.get("code") or "http_error"),
        str(error.get("message") or text or exc.reason),
        details=error.get("details"),
        request_id=error.get("request_id") or exc.headers.get("x-request-id"),
    )


def request_json(method: str, url: str, *, headers: dict[str, str] | None = None, data: Any = None,
                 timeout: int = 30, retries: int = 3) -> Any:
    body = None if data is None else json.dumps(data).encode("utf-8")
    hdrs = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        hdrs.setdefault("Content-Type", "application/json")
    last: Exception | None = None
    method = method.upper()
    # Retrying an unprotected POST can duplicate tasks or images. Only safe methods and
    # requests carrying an explicit idempotency key are retried automatically.
    retryable = method in {"GET", "HEAD", "OPTIONS"} or "Idempotency-Key" in hdrs
    attempts = retries if retryable else 1
    for attempt in range(attempts):
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                ctype = resp.headers.get("Content-Type", "")
                return json.loads(raw.decode("utf-8")) if "json" in ctype or raw[:1] in {b"{", b"["} else raw.decode("utf-8")
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            error = api_error_from_http(exc, text)
            if retryable and (exc.code == 429 or exc.code >= 500) and attempt + 1 < attempts:
                last = error
                retry_after = None
                if isinstance(error.details, dict):
                    retry_after = error.details.get("retry_after_seconds")
                time.sleep(float(retry_after) if retry_after is not None else 2 ** attempt)
                continue
            raise error from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Request failed after {attempts} attempt(s): {last}") from exc
    raise RuntimeError(f"Request failed after {attempts} attempt(s): {last}")
