import unittest
import tempfile
import json
import zipfile
import os
from pathlib import Path
from unittest.mock import patch

from scripts.agent_manager import AgentManager
from scripts.asterfire_client import AsterfireClient
from scripts.kit_manager import KitManager
from scripts.mirror_manager import MirrorManager
from scripts.config import Settings, load_standard_env
from scripts.project_publish import ProjectPublisher
from scripts.task_runner import TaskRunner
from scripts.workflow_manager import WorkflowManager


class FakeClient:
    def __init__(self):
        self.calls = []
        self.responses = []

    def get(self, path, *, params=None):
        self.calls.append(("GET", path, params, None))
        return self.responses.pop(0) if self.responses else {}

    def post(self, path, data=None, *, params=None, headers=None):
        self.calls.append(("POST", path, params, data, headers))
        return self.responses.pop(0) if self.responses else {}

    def delete(self, path):
        self.calls.append(("DELETE", path, None, None))
        return {"deleted": True}

    def wait_async_task(self, task_id, timeout=1800, interval=5):
        self.calls.append(("WAIT_DEV", str(task_id), timeout, interval))
        return {"status": "completed"}

    def upload_toolbox(self, zip_path, force=False):
        self.calls.append(("UPLOAD_TOOLBOX", str(zip_path), force, None))
        return {"toolbox": {"name": "demo-kit"}}


class TestOpenAPIV1Client(unittest.TestCase):
    @patch("scripts.asterfire_client.request_json")
    def test_base_url_header_and_envelope(self, request):
        request.return_value = {"success": True, "data": {"id": 7}}
        client = AsterfireClient("https://example.test", "secret")
        self.assertEqual(client.info(), {"id": 7})
        args, kwargs = request.call_args
        self.assertEqual(args[:2], ("GET", "https://example.test/api/open/v1/info"))
        self.assertEqual(kwargs["headers"], {"Asterfire-Token": "secret"})

    def test_already_versioned_base_is_not_duplicated(self):
        client = AsterfireClient("https://example.test/api/open/v1/", "secret")
        self.assertEqual(client.endpoint, "https://example.test/api/open/v1")

    def test_standard_env_loads_nearest_file_without_overriding_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "project" / "kit"
            child.mkdir(parents=True)
            (root / "project" / ".env").write_text(
                "ASTERFIRE_TEST_FROM_FILE=loaded\n"
                "ASTERFIRE_TEST_EXISTING=from-file\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"ASTERFIRE_TEST_EXISTING": "from-process"}, clear=False):
                os.environ.pop("ASTERFIRE_TEST_FROM_FILE", None)
                loaded = load_standard_env(child)
                self.assertEqual(os.environ["ASTERFIRE_TEST_FROM_FILE"], "loaded")
                self.assertEqual(os.environ["ASTERFIRE_TEST_EXISTING"], "from-process")
                self.assertEqual(loaded, [root / "project" / ".env"])
                os.environ.pop("ASTERFIRE_TEST_FROM_FILE", None)


class TestOpenAPIManagers(unittest.TestCase):
    def test_image_create_then_build_contract(self):
        client = FakeClient()
        client.responses = [{"id": 9}, {"task_id": 31}]
        manager = MirrorManager(client)
        image = manager.create_from_docker("demo", "1.0.0", "acr/demo:1.0.0")
        build = manager.build(image["id"], ["sai"])
        self.assertEqual(client.calls[0][1], "/dev/images")
        self.assertEqual(client.calls[0][3]["source_type"], "docker")
        self.assertEqual(client.calls[1][1], "/dev/images/9/build")
        self.assertEqual(build["task_id"], 31)

    def test_image_conversion_waits_on_cluster_status(self):
        client = FakeClient()
        client.responses = [
            {"cluster_build_status": {"sai": "building"}},
            {"id": 9, "cluster_build_status": {"sai": "success"}},
        ]
        result = MirrorManager(client).wait_conversion(
            {"task_id": "opaque-uuid"}, image_id=9,
            target_clusters=["sai"], timeout=1, interval=0,
        )
        self.assertEqual(result["id"], 9)
        self.assertEqual(client.calls[0][1], "/dev/images/9")

    def test_kit_submit_contract(self):
        client = FakeClient()
        client.responses = [{"task_id": 1, "step_id": 2}]
        result = KitManager(client).run("demo-kit", {"x": 1}, workspace_id=3)
        self.assertEqual(result["step_id"], 2)
        self.assertEqual(client.calls[0][1], "/kits/submit")
        self.assertEqual(client.calls[0][3], {"toolbox": "demo-kit", "input": {"x": 1}, "workspace_id": 3})

    def test_toolbox_upload_rejects_case_only_name_collision(self):
        client = FakeClient()
        client.responses = [{"toolboxes": [{"name": "Protenix"}]}]
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "protenix.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr(
                    "config/configure.json",
                    json.dumps({"name": "protenix", "version": "1.0.0"}),
                )
            with self.assertRaisesRegex(RuntimeError, "differs only by case"):
                KitManager(client).upload(package)
        self.assertEqual(client.calls[0][1], "/dev/toolboxes")

    def test_toolbox_upload_allows_distinct_name(self):
        client = FakeClient()
        client.responses = [{"toolboxes": [{"name": "Protenix"}]}]
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "protenix-mini-kit.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr(
                    "config/configure.json",
                    json.dumps({"name": "protenix-mini-kit", "version": "1.0.1"}),
                )
            result = KitManager(client).upload(package)
        self.assertEqual(result["toolbox"]["name"], "demo-kit")
        self.assertEqual(client.calls[-1][0], "UPLOAD_TOOLBOX")

    def test_agent_uses_snake_case_file_ids(self):
        client = FakeClient()
        client.responses = [{"task_id": "4"}]
        AgentManager(client).create_task("demo-agent", "hello", file_ids=["f1"])
        self.assertEqual(client.calls[0][1], "/tasks")
        self.assertEqual(client.calls[0][3]["file_ids"], ["f1"])
        self.assertNotIn("fileIds", client.calls[0][3])

    def test_workflow_execute_has_idempotency_key(self):
        client = FakeClient()
        client.responses = [{"execution_id": 8}]
        WorkflowManager(client).execute(42, idempotency_key="fixed")
        call = client.calls[0]
        self.assertEqual(call[1], "/workflows/42/execute")
        self.assertEqual(call[2], {"no_cache": "false"})
        self.assertEqual(call[4], {"Idempotency-Key": "fixed"})

    def test_task_runner_passes_step_id_and_waits_for_terminal_state(self):
        client = FakeClient()
        client.responses = [
            {"job_status": "RUNNING", "is_thinking": True},
            {"job_status": "COMPLETED", "is_thinking": False},
        ]
        result = TaskRunner(client).wait_task(7, step_id=11, timeout=1, interval=0)
        self.assertEqual(result["job_status"], "COMPLETED")
        self.assertEqual(client.calls[0][2], {"step_id": 11})

    def test_full_publish_dry_run_reaches_smoke_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Dockerfile").write_text(
                "FROM python:3.11\n"
                "RUN command -v bash && command -v python && python --version "
                "&& python -c \"import adam_community\"\n",
                encoding="utf-8",
            )
            (root / "runner.py").write_text(
                "class Tool: pass\nclass runner(Tool):\n    SIF = 'old:0.1.0'\n",
                encoding="utf-8",
            )
            result = ProjectPublisher(Settings(), dry_run=True).publish_kit(
                str(root), project_name="demo", target_clusters=["sai"],
                smoke_input={"value": 1},
            )
        self.assertEqual(result["target_clusters"], ["sai"])
        self.assertEqual(result["image_build"]["task_id"], "dry-run")
        self.assertTrue(result["smoke_test"]["dry_run"])


if __name__ == "__main__":
    unittest.main()
