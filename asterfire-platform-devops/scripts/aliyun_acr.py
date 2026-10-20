from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class ACRRepository:
    instance_id: str
    repo_id: str
    registry_domain: str
    namespace: str
    name: str


class AliyunACR:
    """Enterprise ACR management via official Alibaba Cloud CLI generic RPC calls.

    Personal Edition is intentionally not managed here because current official docs are inconsistent
    about the scope of Personal Edition OpenAPI. Personal push is handled by Docker/Flow credentials.
    """

    def __init__(self, region: str = "cn-hangzhou", dry_run: bool = False):
        self.region = region
        self.dry_run = dry_run

    def _call(self, action: str, **params: Any) -> dict[str, Any]:
        cmd = ["aliyun", "cr", action, "--RegionId", self.region]
        for key, value in params.items():
            if value is None:
                continue
            cmd.extend([f"--{key}", str(value).lower() if isinstance(value, bool) else str(value)])
        cmd += ["--output", "json"]
        print("+", " ".join(shlex.quote(x) for x in cmd))
        if self.dry_run:
            return {}
        if not shutil.which("aliyun"):
            raise RuntimeError("Alibaba Cloud CLI `aliyun` is required for Enterprise ACR resource management")
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        return json.loads(proc.stdout or "{}")

    def resolve_instance_id(self, instance_name: str) -> str:
        data = self._call("ListInstance", InstanceName=instance_name, PageNo=1, PageSize=30)
        matches = [x for x in data.get("Instances", []) if x.get("InstanceName") == instance_name]
        if not matches:
            raise RuntimeError(f"ACR enterprise instance not found: {instance_name}")
        return matches[0]["InstanceId"]

    def ensure_repository(self, instance_name: str, namespace: str, repo: str) -> ACRRepository:
        if self.dry_run:
            print(f"DRY-RUN ensure ACR enterprise repo: region={self.region} instance={instance_name} namespace={namespace} repo={repo}")
            return ACRRepository("<instance-id>", "<repo-id>", "", namespace, repo)
        instance_id = self.resolve_instance_id(instance_name)
        found = self._call("ListRepository", InstanceId=instance_id, RepoNamespaceName=namespace, RepoName=repo, PageNo=1, PageSize=100)
        repos = found.get("Repositories", found.get("Repositories", [])) or found.get("RepoList", []) or []
        item = next((x for x in repos if x.get("RepoName") == repo), None)
        if item is None and not self.dry_run:
            self._call("CreateRepository", InstanceId=instance_id, RepoNamespaceName=namespace,
                       RepoName=repo, RepoType="PRIVATE", Summary=repo, TagImmutability=False)
            found = self._call("ListRepository", InstanceId=instance_id, RepoNamespaceName=namespace, RepoName=repo, PageNo=1, PageSize=100)
            repos = found.get("Repositories", []) or found.get("RepoList", []) or []
            item = next((x for x in repos if x.get("RepoName") == repo), None)
        repo_id = (item or {}).get("RepoId", "")
        endpoint = self._call("ListInstanceEndpoint", InstanceId=instance_id, ModuleName="Registry", Summary=True)
        registry_domain = ""
        for ep in endpoint.get("Endpoints", []):
            if ep.get("EndpointType") == "internet" and ep.get("Enable", True):
                domains = ep.get("Domains", [])
                if domains:
                    registry_domain = domains[0].get("Domain", "")
                    break
        return ACRRepository(instance_id, repo_id, registry_domain, namespace, repo)

    def list_tags(self, instance_id: str, repo_id: str) -> list[str]:
        if not repo_id:
            return []
        data = self._call("ListRepoTag", InstanceId=instance_id, RepoId=repo_id, PageNo=1, PageSize=100)
        return [x.get("Tag", "") for x in data.get("Images", []) if x.get("Tag")]
