from __future__ import annotations

import time
from typing import Any

from .asterfire_client import AsterfireClient


class MirrorManager:
    def __init__(self, client: AsterfireClient, dry_run: bool = False):
        self.client = client
        self.dry_run = dry_run

    def create_from_docker(self, name: str, version: str, docker_url: str, remark: str = "") -> dict[str, Any]:
        payload = {"name": name, "version": version, "source_type": "docker",
                   "docker_url": docker_url, "remark": remark}
        if self.dry_run:
            print("DRY-RUN POST /dev/images", payload)
            return {"id": "dry-run", "name": name, "version": version, "source_type": "docker"}
        return self.client.post("/dev/images", payload)

    def create_from_sif_file(self, name: str, version: str, file_id: str, remark: str = "") -> dict[str, Any]:
        payload = {"name": name, "version": version, "source_type": "file",
                   "file_id": file_id, "remark": remark}
        if self.dry_run:
            print("DRY-RUN POST /dev/images", payload)
            return {"id": "dry-run", "name": name, "version": version, "source_type": "file"}
        return self.client.post("/dev/images", payload)

    def list(self, *, page: int = 1, per_page: int | None = None,
             name: str | None = None, version: str | None = None) -> Any:
        return self.client.get("/dev/images", params={"page": page, "per_page": per_page,
                                                       "name": name, "version": version})

    def get(self, image_id: int | str) -> Any:
        return self.client.get(f"/dev/images/{image_id}")

    def list_build_clusters(self, image_id: int | str | None = None) -> Any:
        return self.client.get("/dev/images/build-clusters", params={"sif_id": image_id})

    def build(self, image_id: int | str, target_cluster_codes: list[str],
              file_id: str | None = None) -> dict[str, Any]:
        if not target_cluster_codes:
            raise ValueError("target_cluster_codes must not be empty")
        payload: dict[str, Any] = {"target_cluster_codes": target_cluster_codes}
        if file_id:
            payload["file_id"] = file_id
        if self.dry_run:
            print(f"DRY-RUN POST /dev/images/{image_id}/build", payload)
            return {"task_id": "dry-run", "clusters": target_cluster_codes}
        return self.client.post(f"/dev/images/{image_id}/build", payload)

    def get_async_task_log(self, task_id: int | str, step_id: int | str,
                           stream: str = "stdout") -> str:
        if stream not in {"stdout", "stderr"}:
            raise ValueError("stream must be stdout or stderr")
        return self.client.get(f"/dev/async-tasks/{task_id}/log",
                               params={"step_id": step_id, "stream": stream})

    def choose_build_clusters(self, image_id: int | str,
                              requested: list[str] | None = None) -> list[str]:
        if requested:
            return requested
        if self.dry_run:
            return ["<target-cluster>"]
        response = self.list_build_clusters(image_id)
        clusters = response.get("clusters", [])
        defaults = [str(c["code"]) for c in clusters if c.get("is_default_target") and c.get("code")]
        if defaults:
            return defaults
        available = [str(c["code"]) for c in clusters if c.get("code") and str(c.get("status", "")).lower() not in {"offline", "disabled"}]
        if len(available) == 1:
            return available
        raise RuntimeError("No unambiguous default SIF build cluster; pass --target-cluster explicitly")

    def delete(self, mirror_id: int | str, *, yes: bool = False) -> Any:
        if not yes:
            raise RuntimeError("Refusing destructive mirror delete without explicit yes=True / --yes")
        if self.dry_run:
            print(f"DRY-RUN DELETE /dev/images/{mirror_id}")
            return {"dry_run": True, "id": mirror_id}
        return self.client.delete(f"/dev/images/{mirror_id}")

    def wait_conversion(self, response: dict[str, Any], timeout: int = 1800,
                        *, image_id: int | str | None = None,
                        target_clusters: list[str] | None = None,
                        interval: int = 5) -> Any:
        # Current Open API builds can return a UUID task_id and a numeric
        # async_task_id that are not readable through /dev/async-tasks.  The
        # image record is the authoritative source for per-cluster conversion
        # state, so prefer it whenever the caller knows the image id.
        if image_id is not None:
            if self.dry_run:
                return response
            deadline = time.monotonic() + timeout
            success = {"completed", "succeeded", "success", "finished", "done", "available"}
            failure = {"failed", "error", "cancelled", "canceled"}
            while time.monotonic() < deadline:
                image = self.get(image_id)
                statuses = image.get("cluster_build_status") or {}
                selected = target_clusters or list(statuses)
                normalized = {cluster: str(statuses.get(cluster, "")).lower()
                              for cluster in selected}
                if selected and all(normalized.get(cluster) in success for cluster in selected):
                    return image
                failed = {cluster: status for cluster, status in normalized.items()
                          if status in failure}
                if failed:
                    raise RuntimeError(
                        image.get("error") or image.get("error_message")
                        or f"SIF conversion failed for image {image_id}: {failed}"
                    )
                time.sleep(interval)
            raise TimeoutError(f"SIF image {image_id} did not finish in {timeout}s")

        task_id = response.get("task_id") or response.get("async_task_id")
        if not task_id or task_id == "dry-run":
            return response
        return self.client.wait_async_task(str(task_id), timeout=timeout)
