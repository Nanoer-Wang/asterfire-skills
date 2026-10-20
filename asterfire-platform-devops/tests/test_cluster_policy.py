import tempfile
import unittest
from pathlib import Path
from scripts.policies import choose_yunxiao_cluster, dockerfile_needs_external_network

class TestClusterPolicy(unittest.TestCase):
    def test_cluster(self):
        self.assertEqual(choose_yunxiao_cluster(True), "public/cn-hongkong")
        self.assertEqual(choose_yunxiao_cluster(False), "public/cn-beijing")

    def test_dockerfile_scan(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "Dockerfile"
            p.write_text("FROM python:3.11-slim\nRUN pip install requests\n", encoding="utf-8")
            self.assertTrue(dockerfile_needs_external_network(p))

if __name__ == "__main__":
    unittest.main()
