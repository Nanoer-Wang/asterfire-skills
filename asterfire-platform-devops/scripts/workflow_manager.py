from __future__ import annotations

import time
import uuid
from typing import Any

from .asterfire_client import AsterfireClient


class WorkflowManager:
    """Minimal Open API v1 support for invoking already configured workflows."""

    def __init__(self, client: AsterfireClient):
        self.client = client

    def list(self, *, workspace_id: int | None = None,
             folder_id: int | None = None, status: str | None = None) -> Any:
        return self.client.get("/workflows", params={"workspace_id": workspace_id,
                                                      "folder_id": folder_id,
                                                      "status": status})

    def get(self, plan_id: int | str) -> Any:
        return self.client.get(f"/workflows/{plan_id}")

    def execute(self, plan_id: int | str, *, use_default_inputs: bool = True,
                inherit_inputs_from: int | None = None, no_cache: bool = False,
                idempotency_key: str | None = None) -> Any:
        payload: dict[str, Any] = {"use_default_inputs": use_default_inputs}
        if inherit_inputs_from is not None:
            payload["inherit_inputs_from"] = inherit_inputs_from
        key = idempotency_key or str(uuid.uuid4())
        return self.client.post(
            f"/workflows/{plan_id}/execute",
            payload,
            params={"no_cache": str(no_cache).lower()},
            headers={"Idempotency-Key": key},
        )

    def get_execution_status(self, plan_id: int | str,
                             execution_id: int | str) -> Any:
        return self.client.get(f"/workflows/{plan_id}/executions/{execution_id}/status")

    def wait_execution(self, plan_id: int | str, execution_id: int | str, *,
                       timeout: int = 3600, interval: int = 5) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.get_execution_status(plan_id, execution_id)
            status = str(result.get("status", result.get("execution_status", ""))).lower()
            if status in {"completed", "succeeded", "success", "finished", "done"}:
                return result
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(f"Workflow execution {execution_id} failed: {result}")
            time.sleep(interval)
        raise TimeoutError(f"Workflow execution {execution_id} did not finish in {timeout}s")

    def invoke(self, plan_id: int | str, *, timeout: int = 3600,
               interval: int = 5, **kwargs: Any) -> dict[str, Any]:
        result = self.execute(plan_id, **kwargs)
        execution_id = result.get("execution_id")
        if execution_id is None:
            raise RuntimeError(f"Workflow execution did not return execution_id: {result}")
        status = self.wait_execution(plan_id, execution_id, timeout=timeout, interval=interval)
        return {"submission": result, "status": status}
