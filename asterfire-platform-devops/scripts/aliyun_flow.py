from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from .http_utils import request_json
from .policies import choose_yunxiao_cluster, pipeline_name


@dataclass
class PipelineSpec:
    name: str
    content: str
    cluster: str


def _yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_acr_pipeline_yaml(*, codeup_repo: str, branch: str, codeup_service_connection: str,
                            acr_service_connection: str, registry_domain: str, namespace: str,
                            repository: str, tag: str, dockerfile_path: str,
                            region: str = "cn-hangzhou", internet_required: bool,
                            build_container: str, platform: str = "linux/amd64",
                            acr_edition: str = "enterprise", instance_name: str = "") -> str:
    if platform.lower() != "linux/amd64":
        raise ValueError("This skill defaults to and currently generates Yunxiao public builds for linux/amd64")
    cluster = choose_yunxiao_cluster(internet_required)
    source = f'''sources:\n  source_repo:\n    type: codeup\n    name: source_repo\n    endpoint: {_yaml_quote(codeup_repo)}\n    branch: {_yaml_quote(branch)}\n    certificate:\n      type: serviceConnection\n      serviceConnection: {_yaml_quote(codeup_service_connection)}\ndefaultWorkspace: source_repo\n'''
    if acr_edition == "enterprise":
        if not instance_name.strip():
            raise ValueError("ACR Enterprise builds require the exact Flow UI instance value")
        step = f'''          acr_build:\n            step: DockerBuildPushACREE\n            name: 镜像构建并推送至ACR企业版\n            with:\n              serviceConnection: {_yaml_quote(acr_service_connection)}\n              artifact: image\n              region: {_yaml_quote(region)}\n              instance: {_yaml_quote(instance_name)}\n              namespace: {_yaml_quote(namespace)}\n              dockerRegistry: {_yaml_quote(repository)}\n              dockerTag: {_yaml_quote(tag)}\n              dockerfilePath: {_yaml_quote(dockerfile_path)}\n              cacheType: remote\n'''
    else:
        step = f'''          acr_build:\n            step: ACRDockerBuild\n            name: 镜像构建并推送至ACR\n            with:\n              artifact: image\n              dockerfilePath: {_yaml_quote(dockerfile_path)}\n              dockerRegistry: {_yaml_quote(registry_domain)}\n              dockerImage: {_yaml_quote(namespace + "/" + repository)}\n              dockerTag: {_yaml_quote(tag)}\n              region: {_yaml_quote(region)}\n              serviceConnection: {_yaml_quote(acr_service_connection)}\n'''
    return source + f'''stages:\n  build_stage:\n    name: 镜像构建\n    jobs:\n      build_job:\n        name: 镜像构建并推送\n        runsOn:\n          group: {cluster}\n          container: {_yaml_quote(build_container)}\n        steps:\n''' + step


class YunxiaoFlow:
    def __init__(self, domain: str, token: str, *, organization_id: str = "", mode: str = "center", dry_run: bool = False):
        self.domain = domain.rstrip("/")
        self.token = token
        self.organization_id = organization_id
        self.mode = mode
        self.dry_run = dry_run

    @property
    def headers(self) -> dict[str, str]:
        return {"x-yunxiao-token": self.token, "Content-Type": "application/json"}

    def _base(self) -> str:
        if self.mode == "region":
            return f"{self.domain}/oapi/v1/flow"
        if not self.organization_id:
            raise RuntimeError("organization_id is required for Yunxiao center mode")
        return f"{self.domain}/oapi/v1/flow/organizations/{self.organization_id}"

    def create_pipeline(self, name: str, content: str) -> Any:
        if not name.strip():
            raise ValueError("Pipeline name must be concrete and non-empty")
        payload = {"name": name[:60], "content": content}
        if self.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return {"pipelineId": "dry-run", **payload}
        return request_json("POST", f"{self._base()}/pipelines", headers=self.headers, data=payload)

    def run_pipeline(self, pipeline_id: str, params: dict[str, Any] | None = None) -> Any:
        payload = {"params": json.dumps(params or {}, ensure_ascii=False)}
        if self.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return {"pipelineRunId": "dry-run"}
        return request_json("POST", f"{self._base()}/pipelines/{pipeline_id}/runs", headers=self.headers, data=payload)

    def get_run(self, pipeline_id: str, run_id: str) -> Any:
        return request_json("GET", f"{self._base()}/pipelines/{pipeline_id}/runs/{run_id}", headers=self.headers)

    def wait_run(self, pipeline_id: str, run_id: str, timeout: int = 3600, interval: int = 10) -> Any:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = self.get_run(pipeline_id, run_id)
            status = str(data.get("status") or data.get("pipelineRunStatus") or "").upper()
            if status in {"SUCCESS", "SUCCEEDED"}:
                return data
            if status in {"FAIL", "FAILED", "CANCELED", "CANCELLED"}:
                raise RuntimeError(f"Yunxiao pipeline failed: {data}")
            time.sleep(interval)
        raise TimeoutError(f"Yunxiao pipeline {run_id} did not finish in {timeout}s")


def make_pipeline_spec(project: str, artifact: str, version: str, *, internet_required: bool, content: str) -> PipelineSpec:
    return PipelineSpec(
        name=pipeline_name(project, artifact, version, "build"),
        content=content,
        cluster=choose_yunxiao_cluster(internet_required),
    )
