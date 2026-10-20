from __future__ import annotations

import json
import mimetypes
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from .http_utils import APIRequestError, api_error_from_http, request_json


class AsterfireClient:
    def __init__(self, endpoint: str, token: str):
        self.endpoint = self._normalize_endpoint(endpoint)
        self.token = token

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        endpoint = endpoint.rstrip("/")
        if endpoint.endswith("/api/open/v1"):
            return endpoint
        if endpoint.endswith("/api"):
            return f"{endpoint}/open/v1"
        return f"{endpoint}/api/open/v1"

    @property
    def headers(self) -> dict[str, str]:
        return {"Asterfire-Token": self.token}

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        url = f"{self.endpoint}/{path.lstrip('/')}"
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean, doseq=True)}"
        return url

    @staticmethod
    def _unwrap(response: Any) -> Any:
        if not isinstance(response, dict) or "success" not in response:
            return response
        if response.get("success") is True:
            return response.get("data", {})
        error = response.get("error", {})
        raise APIRequestError(
            200,
            str(error.get("code") or "api_error"),
            str(error.get("message") or "AsterFire API request failed"),
            details=error.get("details"),
            request_id=error.get("request_id"),
        )

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self._unwrap(request_json("GET", self._url(path, params), headers=self.headers))

    def post(self, path: str, data: dict[str, Any] | None = None, *,
             params: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None) -> Any:
        merged = {**self.headers, **(headers or {})}
        return self._unwrap(request_json("POST", self._url(path, params), headers=merged, data=data or {}))

    def put(self, path: str, data: dict[str, Any]) -> Any:
        return self._unwrap(request_json("PUT", self._url(path), headers=self.headers, data=data))

    def patch(self, path: str, data: dict[str, Any]) -> Any:
        return self._unwrap(request_json("PATCH", self._url(path), headers=self.headers, data=data))

    def delete(self, path: str) -> Any:
        return self._unwrap(request_json("DELETE", self._url(path), headers=self.headers))

    def info(self) -> dict[str, Any]:
        return self.get("/info")

    def health(self) -> dict[str, Any]:
        return self.get("/health")

    def list_toolboxes(self, toolbox_type: str = "agent") -> dict[str, Any]:
        return self.get("/toolboxes", params={"type": toolbox_type})

    def upload_file(self, path: str | Path, *, task_id: str | None = None) -> Any:
        fields = {"task_id": task_id} if task_id else {}
        return self._multipart("/files/upload", path, fields)

    def upload_toolbox(self, zip_path: str | Path, *, force: bool = False) -> Any:
        return self._multipart("/dev/toolboxes", zip_path, {"force": str(force).lower()})

    def _multipart(self, api_path: str, file_path: str | Path, fields: dict[str, str | None]) -> Any:
        file_path = Path(file_path)
        boundary = f"----asterfire-{uuid.uuid4().hex}"
        chunks: list[bytes] = []
        for name, value in fields.items():
            if value is None:
                continue
            chunks += [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode(), b"\r\n",
            ]
        mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        chunks += [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            file_path.read_bytes(), b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        req = urllib.request.Request(
            self._url(api_path), data=b"".join(chunks), method="POST",
            headers={**self.headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
                return self._unwrap(json.loads(raw) if raw else {})
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            raise api_error_from_http(exc, text) from exc

    def list_task_files(self, path: str, *, workspace_id: int | None = None) -> Any:
        return self.get("/tasks/files", params={"path": path, "workspace_id": workspace_id})

    def download_file(self, file_id: str, destination: str | Path, *,
                      workspace_id: int | None = None) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            self._url(f"/files/{urllib.parse.quote(str(file_id), safe='')}/download",
                      {"workspace_id": workspace_id}),
            headers=self.headers,
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp, destination.open("wb") as out:
                shutil.copyfileobj(resp, out)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            raise api_error_from_http(exc, text) from exc
        return destination

    def wait_async_task(self, task_id: str, timeout: int = 1800, interval: int = 5) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            payload = self.get(f"/dev/async-tasks/{task_id}")
            status = str(payload.get("status", "")).lower()
            if status in {"completed", "succeeded", "success", "finished", "done"}:
                return payload
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(payload.get("error_message") or f"Async task {task_id} failed: {payload}")
            time.sleep(interval)
        raise TimeoutError(f"Async task {task_id} did not finish in {timeout}s")
