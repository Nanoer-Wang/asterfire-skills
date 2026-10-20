from __future__ import annotations

from pathlib import Path
import os
from typing import Any

from .aliyun_acr import AliyunACR
from .aliyun_flow import YunxiaoFlow, build_acr_pipeline_yaml, make_pipeline_spec
from .asterfire_client import AsterfireClient
from .config import Settings
from .docker_local import LocalDocker
from .kit_manager import KitManager
from .mirror_manager import MirrorManager
from .policies import next_image_tag, resolve_internet_requirement
from .runtime_contract import validate_runtime_contract


class ProjectPublisher:
    def __init__(self, settings: Settings, dry_run: bool = False):
        self.s = settings
        self.dry_run = dry_run

    def publish_kit(self, project_dir: str, *, project_name: str, dockerfile: str | None = None,
                    tag: str | None = None, overwrite_tag: str | None = None,
                    codeup_repo: str | None = None, branch: str | None = None,
                    target_clusters: list[str] | None = None,
                    smoke_input: dict[str, Any] | None = None) -> dict[str, Any]:
        root = Path(project_dir).resolve()
        dockerfile_path = Path(dockerfile or self.s.build.dockerfile)
        if not dockerfile_path.is_absolute():
            dockerfile_path = root / dockerfile_path
        if not dockerfile_path.exists():
            raise FileNotFoundError(dockerfile_path)
        validate_runtime_contract(dockerfile_path)

        repo_name = self.s.acr.repository or project_name.lower()
        acr_repo = None
        existing_tags: list[str] = []
        registry_domain = self.s.acr.registry_domain
        if self.s.acr.edition == "enterprise":
            # A fixed tag plus an explicit registry domain is enough for a Yunxiao
            # service connection to perform the push.  Do not make the local
            # Alibaba Cloud CLI a hard dependency in that case: many developers
            # can use the shared Flow/ACR connection but do not own RAM keys.
            # Repository existence and push permission are then validated by the
            # real DockerBuildPushACREE job.
            if not (tag and registry_domain and self.s.build.backend == "yunxiao"):
                acr = AliyunACR(self.s.acr.region, dry_run=self.dry_run)
                acr_repo = acr.ensure_repository(self.s.acr.instance_name, self.s.acr.namespace, repo_name)
                registry_domain = registry_domain or acr_repo.registry_domain
                if not self.dry_run:
                    existing_tags = acr.list_tags(acr_repo.instance_id, acr_repo.repo_id)
        if not registry_domain:
            if self.dry_run:
                registry_domain = "<registry-domain>"
            else:
                raise RuntimeError("registry_domain could not be resolved; set acr.registry_domain explicitly")

        selected_tag = tag or next_image_tag(existing_tags, overwrite=overwrite_tag)
        image_url = f"{registry_domain}/{self.s.acr.namespace}/{repo_name}:{selected_tag}"
        internet_required = resolve_internet_requirement(self.s.build.internet_required, dockerfile_path)

        if self.s.build.backend == "local":
            docker = LocalDocker(self.dry_run)
            local_tag = f"{repo_name}:{selected_tag}"
            docker.build(root, dockerfile_path, local_tag, self.s.build.platform)
            docker.login(registry_domain, self.s.acr.username_env, self.s.acr.password_env)
            docker.tag(local_tag, image_url)
            docker.push(image_url)
        elif self.s.build.backend == "yunxiao":
            repo_url = codeup_repo or self.s.yunxiao.codeup_repo
            if not repo_url:
                raise RuntimeError("A Codeup repository URL is required for Yunxiao builds")
            codeup_sc = (os.getenv(self.s.yunxiao.codeup_service_connection_env, "")
                         or ("<codeup-service-connection>" if self.dry_run else ""))
            acr_sc = (os.getenv(self.s.yunxiao.acr_service_connection_env, "")
                      or ("<acr-service-connection>" if self.dry_run else ""))
            if not codeup_sc:
                raise RuntimeError(f"Missing environment variable: {self.s.yunxiao.codeup_service_connection_env}")
            if not acr_sc:
                raise RuntimeError(f"Missing environment variable: {self.s.yunxiao.acr_service_connection_env}")
            content = build_acr_pipeline_yaml(
                codeup_repo=repo_url,
                branch=branch or self.s.yunxiao.branch,
                codeup_service_connection=codeup_sc,
                acr_service_connection=acr_sc,
                registry_domain=registry_domain,
                namespace=self.s.acr.namespace,
                repository=repo_name,
                tag=selected_tag,
                dockerfile_path=dockerfile_path.relative_to(root).as_posix(),
                region=self.s.acr.region,
                internet_required=internet_required,
                build_container=self.s.yunxiao.build_container,
                platform=self.s.build.platform,
                acr_edition=self.s.acr.edition,
                instance_name=self.s.acr.instance_name,
            )
            spec = make_pipeline_spec(project_name, "image", selected_tag, internet_required=internet_required, content=content)
            flow_domain = self.s.yunxiao.domain or ("https://<yunxiao-domain>" if self.dry_run else "")
            if not flow_domain:
                raise RuntimeError("yunxiao.domain must be configured")
            flow_token = (os.getenv(self.s.yunxiao.token_env, "")
                          or ("<yunxiao-token>" if self.dry_run else ""))
            if not flow_token:
                raise RuntimeError(f"Missing environment variable: {self.s.yunxiao.token_env}")
            if self.s.yunxiao.mode == "region":
                org_id = ""
            else:
                org_id = (os.getenv(self.s.yunxiao.organization_id_env, "")
                          or ("<organization-id>" if self.dry_run else ""))
                if not org_id:
                    raise RuntimeError(f"Missing environment variable: {self.s.yunxiao.organization_id_env}")
            flow = YunxiaoFlow(flow_domain, flow_token, organization_id=org_id,
                                mode=self.s.yunxiao.mode, dry_run=self.dry_run)
            created = flow.create_pipeline(spec.name, spec.content)
            pipeline_id = (str(created) if isinstance(created, (int, str)) else
                           str(created.get("pipelineId") or created.get("id") or
                               created.get("data", {}).get("pipelineId") or ""))
            if not pipeline_id:
                raise RuntimeError(f"Cannot extract pipelineId from response: {created}")
            run = flow.run_pipeline(pipeline_id)
            run_id = (str(run) if isinstance(run, (int, str)) else
                      str(run.get("pipelineRunId") or run.get("id") or
                          run.get("data", {}).get("pipelineRunId") or ""))
            if run_id and run_id != "dry-run":
                flow.wait_run(pipeline_id, run_id)
        else:
            raise ValueError("build.backend must be local or yunxiao")

        if self.dry_run:
            client = None
            mirror = MirrorManager(None, dry_run=True)  # type: ignore[arg-type]
        else:
            client = AsterfireClient(self.s.asterfire.endpoint, self.s.asterfire.token)
            mirror = MirrorManager(client)

        image_record = mirror.create_from_docker(
            repo_name, selected_tag, image_url, f"{project_name} published by skill"
        )
        image_id = image_record.get("id")
        if image_id is None:
            raise RuntimeError(f"Image creation did not return id: {image_record}")
        clusters = mirror.choose_build_clusters(image_id, target_clusters)
        image_build = mirror.build(image_id, clusters)
        image_build_status = mirror.wait_conversion(
            image_build, image_id=image_id, target_clusters=clusters
        )

        sif = f"{repo_name}:{selected_tag}"
        if client:
            kit = KitManager(client)
        else:
            # token is intentionally not required for a full dry-run.
            class _Dummy: pass
            kit = KitManager(_Dummy(), dry_run=True)  # type: ignore[arg-type]
        kit.update_sif_reference(root, sif)
        zip_path = kit.build_zip(root)
        upload_resp = kit.upload(zip_path)
        smoke_test = None
        if smoke_input is not None:
            toolbox = upload_resp.get("toolbox", {})
            toolbox_name = toolbox.get("name") or project_name
            smoke_test = kit.invoke(str(toolbox_name), smoke_input)
        return {
            "project": project_name,
            "repository": repo_name,
            "tag": selected_tag,
            "image": image_url,
            "sif": sif,
            "internet_required": internet_required,
            "image_record": image_record,
            "image_build": image_build,
            "image_build_status": image_build_status,
            "target_clusters": clusters,
            "toolbox": upload_resp,
            "smoke_test": smoke_test,
        }
