import unittest
from scripts.policies import next_image_tag

class TestVersioning(unittest.TestCase):
    def test_first_tag(self):
        self.assertEqual(next_image_tag([]), "1.0.0")

    def test_patch_increment(self):
        self.assertEqual(next_image_tag(["1.0.0", "1.0.2", "latest"]), "1.0.3")

    def test_overwrite_keeps_tag(self):
        self.assertEqual(next_image_tag(["1.0.0"], overwrite="1.0.0"), "1.0.0")

if __name__ == "__main__":
    unittest.main()
