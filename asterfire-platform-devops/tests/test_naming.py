import unittest
from scripts.policies import pipeline_name

class TestNaming(unittest.TestCase):
    def test_concrete_name(self):
        name = pipeline_name("ProteinMPNN", "image", "1.0.0")
        self.assertEqual(name, "asterfire-proteinmpnn-image-1.0.0-build")
        self.assertLessEqual(len(name), 60)

    def test_name_is_sanitized(self):
        self.assertNotIn(" ", pipeline_name("My Project", "kit", "1.0.0"))

if __name__ == "__main__":
    unittest.main()
