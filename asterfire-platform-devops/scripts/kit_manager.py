from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .asterfire_client import AsterfireClient
from .task_runner import TaskRunner


class KitManager:
    def __init__(self, client: AsterfireClient, dry_run: bool = False):
        self.client = client
        self.dry_run = dry_run

    def update_sif_reference(self, project_dir: str | Path, sif: str) -> Path:
        root = Path(project_dir)
        candidates = []
        for p in root.rglob("*.py"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"class\s+runner\s*\(\s*Tool\s*\)", text):
                candidates.append(p)
        if len(candidates) != 1:
            raise RuntimeError(f"Expected exactly one runner(Tool) entry file, found {len(candidates)}")
        path = candidates[0]
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^\s*SIF\s*=", text):
            text = re.sub(r'(?m)^(\s*SIF\s*=\s*)[\"\'][^\"\']*[\"\']', rf'\1"{sif}"', text, count=1)
        else:
            text = re.sub(r"(class\s+runner\s*\(\s*Tool\s*\)\s*:\s*\n)", rf'\1    SIF = "{sif}"\n', text, count=1)
        if not self.dry_run:
            path.write_text(text, encoding="utf-8")
        else:
            print(f"DRY-RUN update {path}: SIF={sif}")
        return path

    def build_zip(self, project_dir: str | Path) -> Path:
        root = Path(project_dir).resolve()
        if self.dry_run:
            return root.with_suffix(".zip")
        # Prefer adam-cli because upstream skills define it as package truth.
        if shutil.which("adam-cli"):
            proc = subprocess.run(["adam-cli", "build", "."], cwd=root, text=True, capture_output=True)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr or proc.stdout)
            zips = sorted(root.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
            if zips:
                return zips[0]
        target = Path(tempfile.gettempdir()) / root.name
        zip_path = Path(shutil.make_archive(str(target), "zip", root_dir=root.parent, base_dir=root.name))
        return zip_path

    def upload(self, zip_path: str | Path, *, force: bool = False) -> Any:
        if self.dry_run:
            print(f"DRY-RUN upload toolbox: {zip_path}")
            return {"toolbox": {"path": str(zip_path), "name": Path(zip_path).stem}}
        name = self._package_name(zip_path)
        listed = self.client.get("/dev/toolboxes")
        conflicts = sorted({
            str(item.get("name"))
            for item in listed.get("toolboxes", [])
            if item.get("name")
            and str(item["name"]).casefold() == name.casefold()
            and str(item["name"]) != name
        })
        if conflicts:
            raise RuntimeError(
                f"Toolbox name {name!r} differs only by case from existing "
                f"toolbox name(s) {conflicts}. The developer UI resolves "
                "application versions by name and may show an empty or "
                "unauthorized version list. Choose a distinct name."
            )
        return self.client.upload_toolbox(zip_path, force=force)

    @staticmethod
    def _package_name(zip_path: str | Path) -> str:
        try:
            with zipfile.ZipFile(zip_path) as archive:
                configure = json.loads(archive.read("config/configure.json"))
        except (KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            raise RuntimeError(
                f"Cannot read config/configure.json from toolbox package: {zip_path}"
            ) from exc
        name = str(configure.get("name") or "").strip()
        if not name:
            raise RuntimeError("Toolbox config/configure.json is missing a non-empty name")
        return name

    def run(self, toolbox: str, input_data: dict[str, Any], workspace_id: int | None = None) -> Any:
        payload: dict[str, Any] = {"toolbox": toolbox, "input": input_data}
        if workspace_id is not None:
            payload["workspace_id"] = workspace_id
        if self.dry_run:
            print("DRY-RUN POST /kits/submit", payload)
            return {"task_id": "dry-run", "step_id": "dry-run", "message": "dry-run"}
        return self.client.post("/kits/submit", payload)

    def run_in_task(self, task_id: int | str, kit_name: str,
                    input_data: dict[str, Any]) -> Any:
        if self.dry_run:
            payload = {"kit_name": kit_name, "input": input_data}
            print(f"DRY-RUN POST /tasks/{task_id}/kit-run", payload)
            return {"pipeline_id": "dry-run", "step_id": "dry-run", "message": "dry-run"}
        return self.client.post(
            f"/tasks/{task_id}/kit-run",
            {"kit_name": kit_name, "input": input_data},
        )

    def invoke(self, toolbox: str, input_data: dict[str, Any], *,
               workspace_id: int | None = None, timeout: int = 3600,
               interval: int = 5, output_dir: str | Path | None = None) -> dict[str, Any]:
        submission = self.run(toolbox, input_data, workspace_id)
        if self.dry_run:
            return {"submission": submission, "dry_run": True}
        task_id = submission.get("task_id")
        if task_id is None:
            raise RuntimeError(f"Kit submission did not return task_id: {submission}")
        runner = TaskRunner(self.client)
        status = runner.wait_task(task_id, step_id=submission.get("step_id"),
                                  timeout=timeout, interval=interval)
        result = {"submission": submission, "status": status,
                  "task": runner.get_task(task_id)}
        if output_dir is not None:
            result["downloaded_files"] = runner.download_task_files(task_id, output_dir)
        return result
