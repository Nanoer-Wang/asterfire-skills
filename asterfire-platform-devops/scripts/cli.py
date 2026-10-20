from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent_manager import AgentManager
from .asterfire_client import AsterfireClient
from .config import load_settings, load_standard_env
from .docker_local import LocalDocker
from .kit_manager import KitManager
from .mirror_manager import MirrorManager
from .project_publish import ProjectPublisher
from .workflow_manager import WorkflowManager


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "templates" / "asterfire.yaml"


def _json_arg(value: str) -> dict:
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _print(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="asterfire-platform-devops")
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="domain", required=True)

    project = sub.add_parser("project")
    project_sub = project.add_subparsers(dest="action", required=True)
    _add_publish_args(project_sub.add_parser("publish"))

    image = sub.add_parser("image")
    image_sub = image.add_subparsers(dest="action", required=True)
    ib = image_sub.add_parser("build-local")
    ib.add_argument("--path", required=True)
    ib.add_argument("--name", required=True)
    ib.add_argument("--tag", default="1.0.0")
    ib.add_argument("--dockerfile", default="Dockerfile")
    il = image_sub.add_parser("list")
    il.add_argument("--name")
    il.add_argument("--version")
    il.add_argument("--page", type=int, default=1)
    il.add_argument("--per-page", type=int)
    ig = image_sub.add_parser("get")
    ig.add_argument("--image-id", required=True)
    ie = image_sub.add_parser("build-existing")
    ie.add_argument("--image-id", required=True)
    ie.add_argument("--target-cluster", action="append", dest="target_clusters")
    ir = image_sub.add_parser("register")
    ir.add_argument("--name", required=True)
    ir.add_argument("--version", required=True)
    ir.add_argument("--docker-url", required=True)
    ir.add_argument("--remark", default="")
    ir.add_argument("--target-cluster", action="append", dest="target_clusters")
    ir.add_argument("--no-build", action="store_true")
    idelete = image_sub.add_parser("delete")
    idelete.add_argument("--image-id", required=True)
    idelete.add_argument("--yes", action="store_true")

    kit = sub.add_parser("kit")
    kit_sub = kit.add_subparsers(dest="action", required=True)
    ku = kit_sub.add_parser("upload")
    ku.add_argument("zip")
    ku.add_argument("--force", action="store_true")
    kr = kit_sub.add_parser("run")
    kr.add_argument("--toolbox", required=True)
    kr.add_argument("--input", required=True)
    kr.add_argument("--workspace-id", type=int)
    kr.add_argument("--timeout", type=int, default=3600)
    kr.add_argument("--output-dir")
    kr.add_argument("--no-wait", action="store_true")

    agent = sub.add_parser("agent")
    agent_sub = agent.add_subparsers(dest="action", required=True)
    au = agent_sub.add_parser("upload")
    au.add_argument("zip")
    au.add_argument("--force", action="store_true")
    ar = agent_sub.add_parser("run")
    ar.add_argument("--toolbox", required=True)
    ar.add_argument("--message", required=True)
    ar.add_argument("--file-id", action="append", dest="file_ids")
    ar.add_argument("--workspace-id", type=int)
    ar.add_argument("--llm-model")
    ar.add_argument("--timeout", type=int, default=3600)
    ar.add_argument("--output-dir")
    ar.add_argument("--no-wait", action="store_true")

    workflow = sub.add_parser("workflow")
    workflow_sub = workflow.add_subparsers(dest="action", required=True)
    workflow_sub.add_parser("list")
    wr = workflow_sub.add_parser("run")
    wr.add_argument("--plan-id", required=True)
    wr.add_argument("--inherit-inputs-from", type=int)
    wr.add_argument("--no-cache", action="store_true")
    wr.add_argument("--idempotency-key")
    wr.add_argument("--timeout", type=int, default=3600)
    wr.add_argument("--no-wait", action="store_true")

    files = sub.add_parser("file")
    files_sub = files.add_subparsers(dest="action", required=True)
    fu = files_sub.add_parser("upload")
    fu.add_argument("path")
    fu.add_argument("--task-id")
    fd = files_sub.add_parser("download")
    fd.add_argument("--file-id", required=True)
    fd.add_argument("--output", required=True)
    fd.add_argument("--workspace-id", type=int)

    sub.add_parser("info")
    return p


def _add_publish_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--dockerfile")
    p.add_argument("--tag")
    p.add_argument("--overwrite-tag")
    p.add_argument("--codeup-repo")
    p.add_argument("--branch")
    p.add_argument("--target-cluster", action="append", dest="target_clusters")
    p.add_argument("--smoke-input", help="JSON string or path; submit only when explicitly provided")


def _publisher_result(args, settings):
    return ProjectPublisher(settings, dry_run=args.dry_run).publish_kit(
        args.path,
        project_name=args.name,
        dockerfile=args.dockerfile,
        tag=args.tag,
        overwrite_tag=args.overwrite_tag,
        codeup_repo=args.codeup_repo,
        branch=args.branch,
        target_clusters=args.target_clusters,
        smoke_input=_json_arg(args.smoke_input) if args.smoke_input else None,
    )


def main() -> None:
    args = parser().parse_args()
    project_path = getattr(args, "path", None)
    load_standard_env(
        project_path or Path.cwd(),
        Path.cwd(),
        Path(args.config).resolve().parent,
    )
    settings = load_settings(args.config)

    if args.domain == "project" and args.action == "publish":
        _print(_publisher_result(args, settings))
        return

    if args.domain == "image" and args.action == "build-local":
        root = Path(args.path).resolve()
        dockerfile = Path(args.dockerfile)
        if not dockerfile.is_absolute():
            dockerfile = root / dockerfile
        LocalDocker(args.dry_run).build(root, dockerfile, f"{args.name}:{args.tag}",
                                        settings.build.platform)
        return

    token = "<dry-run-token>" if args.dry_run else settings.asterfire.token
    client = AsterfireClient(settings.asterfire.endpoint, token)

    if args.domain == "info":
        _print({"dry_run": True, "operation": "GET /info"} if args.dry_run else client.info())
        return

    if args.domain == "image":
        manager = MirrorManager(client, dry_run=args.dry_run)
        if args.action == "list":
            if args.page < 1 or (args.per_page is not None and args.per_page < 1):
                raise SystemExit("image list page/per-page must be positive")
            filters = {"page": args.page, "per_page": args.per_page,
                       "name": args.name, "version": args.version}
            result = ({"dry_run": True, "operation": "GET /dev/images", "query": filters}
                      if args.dry_run else manager.list(**filters))
        elif args.action == "get":
            result = ({"dry_run": True, "operation": f"GET /dev/images/{args.image_id}"}
                      if args.dry_run else manager.get(args.image_id))
        elif args.action == "build-existing":
            clusters = manager.choose_build_clusters(args.image_id, args.target_clusters)
            build = manager.build(args.image_id, clusters)
            result = {
                "image_id": args.image_id,
                "target_clusters": clusters,
                "build": build,
                "build_status": manager.wait_conversion(
                    build, image_id=args.image_id, target_clusters=clusters
                ),
            }
        elif args.action == "register":
            record = manager.create_from_docker(args.name, args.version, args.docker_url, args.remark)
            result = {"image_record": record}
            if not args.no_build:
                clusters = manager.choose_build_clusters(record["id"], args.target_clusters)
                build = manager.build(record["id"], clusters)
                result.update({"target_clusters": clusters, "build": build,
                               "build_status": manager.wait_conversion(
                                   build, image_id=record["id"], target_clusters=clusters
                               )})
        elif args.action == "delete":
            result = manager.delete(args.image_id, yes=args.yes)
        else:
            raise SystemExit("unsupported image action")
        _print(result)
        return

    if args.domain == "kit":
        manager = KitManager(client, dry_run=args.dry_run)
        if args.action == "upload":
            result = manager.upload(args.zip, force=args.force)
        elif args.no_wait:
            result = manager.run(args.toolbox, _json_arg(args.input), args.workspace_id)
        else:
            result = manager.invoke(args.toolbox, _json_arg(args.input),
                                    workspace_id=args.workspace_id, timeout=args.timeout,
                                    output_dir=args.output_dir)
        _print(result)
        return

    if args.domain == "agent":
        if args.action == "upload":
            result = KitManager(client, dry_run=args.dry_run).upload(args.zip, force=args.force)
        else:
            manager = AgentManager(client, dry_run=args.dry_run)
            if args.no_wait:
                result = manager.create_task(args.toolbox, args.message,
                                             file_ids=args.file_ids,
                                             workspace_id=args.workspace_id,
                                             llm_model=args.llm_model)
            else:
                result = manager.invoke(args.toolbox, args.message,
                                        file_ids=args.file_ids,
                                        workspace_id=args.workspace_id,
                                        llm_model=args.llm_model,
                                        timeout=args.timeout,
                                        output_dir=args.output_dir)
        _print(result)
        return

    if args.domain == "workflow":
        if args.dry_run:
            _print({"dry_run": True, "operation": args.action,
                    "plan_id": getattr(args, "plan_id", None)})
            return
        manager = WorkflowManager(client)
        if args.action == "list":
            result = manager.list()
        elif args.no_wait:
            result = manager.execute(args.plan_id,
                                     inherit_inputs_from=args.inherit_inputs_from,
                                     no_cache=args.no_cache,
                                     idempotency_key=args.idempotency_key)
        else:
            result = manager.invoke(args.plan_id,
                                    inherit_inputs_from=args.inherit_inputs_from,
                                    no_cache=args.no_cache,
                                    idempotency_key=args.idempotency_key,
                                    timeout=args.timeout)
        _print(result)
        return

    if args.domain == "file":
        if args.dry_run:
            _print({"dry_run": True, "operation": args.action})
        elif args.action == "upload":
            _print(client.upload_file(args.path, task_id=args.task_id))
        else:
            _print({"path": str(client.download_file(args.file_id, args.output,
                                                     workspace_id=args.workspace_id))})


if __name__ == "__main__":
    main()
