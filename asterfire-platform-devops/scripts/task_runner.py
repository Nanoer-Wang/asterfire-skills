from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .asterfire_client import AsterfireClient


class TaskRunner:
    def __init__(self, client: AsterfireClient):
        self.client = client

    def get_task(self, task_id: int | str, *, limit: int = 100) -> dict[str, Any]:
        return self.client.get(f"/tasks/{task_id}", params={"limit": limit})

    def get_status(self, task_id: int | str, *,
                   step_id: int | str | None = None) -> dict[str, Any]:
        return self.client.get(f"/tasks/{task_id}/status", params={"step_id": step_id})

    def wait_task(self, task_id: int | str, *, step_id: int | str | None = None,
                  timeout: int = 3600, interval: int = 5) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        polls = 0
        while time.monotonic() < deadline:
            status = self.get_status(task_id, step_id=step_id)
            polls += 1
            job = str(status.get("job_status", "")).upper()
            thinking = bool(status.get("is_thinking", False))
            if job in {"FAILED", "ERROR", "CANCELLED", "CANCELED", "TIMEOUT"}:
                raise RuntimeError(f"Task {task_id} failed: {status}")
            if job in {"COMPLETED", "SUCCEEDED", "SUCCESS", "FINISHED", "DONE"}:
                return status
            if not thinking and job and job not in {"PENDING", "RUNNING", "QUEUED", "SUBMITTED"}:
                return status
            if step_id is None and not thinking and polls > 1:
                return status
            time.sleep(interval)
        raise TimeoutError(f"Task {task_id} did not finish in {timeout}s")

    @staticmethod
    def _file_records(task: dict[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        def visit(value: Any, *, in_files: bool = False) -> None:
            if isinstance(value, dict):
                if in_files and value.get("id") and value.get("name"):
                    records.append(value)
                for key, child in value.items():
                    visit(child, in_files=(key == "files"))
            elif isinstance(value, list):
                for child in value:
                    visit(child, in_files=in_files)

        visit(task)
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for record in records:
            file_id = str(record["id"])
            if file_id not in seen:
                seen.add(file_id)
                unique.append(record)
        return unique

    def download_task_files(self, task_id: int | str, output_dir: str | Path) -> list[Path]:
        output_dir = Path(output_dir)
        task = self.get_task(task_id)
        downloaded: list[Path] = []
        for record in self._file_records(task):
            name = Path(str(record["name"])).name
            downloaded.append(self.client.download_file(str(record["id"]), output_dir / name))
        return downloaded
