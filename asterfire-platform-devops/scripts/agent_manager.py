from __future__ import annotations

from pathlib import Path
from typing import Any

from .asterfire_client import AsterfireClient
from .task_runner import TaskRunner


class AgentManager:
    def __init__(self, client: AsterfireClient, dry_run: bool = False):
        self.client = client
        self.dry_run = dry_run

    def create_task(self, toolbox: str, message: str, *, file_ids: list[str] | None = None,
                    workspace_id: int | None = None, folder_id: int | None = None,
                    llm_model: str | None = None) -> Any:
        payload: dict[str, Any] = {"message": message, "toolbox": toolbox,
                                   "file_ids": file_ids or []}
        if workspace_id is not None:
            payload["workspace_id"] = workspace_id
        if folder_id is not None:
            payload["folder_id"] = folder_id
        if llm_model:
            payload["llm_model"] = llm_model
        if self.dry_run:
            print("DRY-RUN POST /tasks", payload)
            return {"task_id": "dry-run"}
        return self.client.post("/tasks", payload)

    def send_message(self, task_id: int | str, message: str,
                     file_ids: list[str] | None = None,
                     llm_model: str | None = None) -> Any:
        payload: dict[str, Any] = {"message": message, "file_ids": file_ids or []}
        if llm_model:
            payload["llm_model"] = llm_model
        if self.dry_run:
            print(f"DRY-RUN POST /tasks/{task_id}/messages", payload)
            return {"task_id": task_id, "dry_run": True}
        return self.client.post(f"/tasks/{task_id}/messages", payload)

    def get_task(self, task_id: int | str, limit: int = 100) -> Any:
        return self.client.get(f"/tasks/{task_id}", params={"limit": limit})

    def list_tasks(self, **filters: Any) -> Any:
        return self.client.get("/tasks", params=filters)

    def get_status(self, task_id: int | str, step_id: int | str | None = None) -> Any:
        return self.client.get(f"/tasks/{task_id}/status", params={"step_id": step_id})

    def stop(self, task_id: int | str) -> Any:
        return self.client.post(f"/tasks/{task_id}/stop")

    def rename(self, task_id: int | str, name: str,
               workspace_id: int | None = None) -> Any:
        payload: dict[str, Any] = {"name": name}
        if workspace_id is not None:
            payload["workspace_id"] = workspace_id
        return self.client.post(f"/tasks/{task_id}/rename", payload)

    def delete(self, task_id: int | str, *, yes: bool = False) -> Any:
        if not yes:
            raise RuntimeError("Refusing destructive task delete without explicit yes=True / --yes")
        return self.client.delete(f"/tasks/{task_id}")

    def invoke(self, toolbox: str, message: str, *, file_ids: list[str] | None = None,
               workspace_id: int | None = None, llm_model: str | None = None,
               timeout: int = 3600, interval: int = 5,
               output_dir: str | Path | None = None) -> dict[str, Any]:
        submission = self.create_task(toolbox, message, file_ids=file_ids,
                                      workspace_id=workspace_id, llm_model=llm_model)
        if self.dry_run:
            return {"submission": submission, "dry_run": True}
        task_id = submission.get("task_id")
        if task_id is None:
            raise RuntimeError(f"Agent task creation did not return task_id: {submission}")
        runner = TaskRunner(self.client)
        status = runner.wait_task(task_id, timeout=timeout, interval=interval)
        result = {"submission": submission, "status": status,
                  "task": runner.get_task(task_id)}
        if output_dir is not None:
            result["downloaded_files"] = runner.download_task_files(task_id, output_dir)
        return result
