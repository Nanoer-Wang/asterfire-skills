import tempfile
import unittest
from pathlib import Path

from scripts.runtime_contract import inspect_runtime_contract, validate_runtime_contract


class TestRuntimeContract(unittest.TestCase):
    def test_rejects_python3_only_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            dockerfile = Path(tmp) / "Dockerfile"
            dockerfile.write_text(
                "FROM ubuntu:22.04\n"
                "RUN apt-get update && apt-get install -y python3 python3-pip "
                "&& python3 --version\n",
                encoding="utf-8",
            )
            problems = inspect_runtime_contract(dockerfile)
            self.assertTrue(any("python 命令" in item for item in problems))
            self.assertTrue(any("adam_community" in item for item in problems))
            with self.assertRaisesRegex(RuntimeError, "停止镜像发布"):
                validate_runtime_contract(dockerfile)

    def test_accepts_complete_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            dockerfile = Path(tmp) / "Dockerfile"
            dockerfile.write_text(
                "FROM python:3.11\n"
                "RUN command -v bash && command -v python && python --version "
                "&& python -c \"import adam_community; print('ready')\"\n",
                encoding="utf-8",
            )
            self.assertEqual(inspect_runtime_contract(dockerfile), [])
            validate_runtime_contract(dockerfile)


if __name__ == "__main__":
    unittest.main()
