import unittest
from pathlib import Path

import yaml


class DockerComposeTests(unittest.TestCase):
    def test_compose_includes_local_ollama_stack(self):
        data = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

        self.assertIn("services", data)
        self.assertIn("ollama", data["services"])
        self.assertIn("ollama-init", data["services"])
        self.assertIn("bhf-web", data["services"])

        ollama = data["services"]["ollama"]
        init = data["services"]["ollama-init"]
        web = data["services"]["bhf-web"]

        self.assertEqual(ollama["image"], "ollama/ollama:latest")
        self.assertEqual(ollama["ports"], ["11434:11434"])
        self.assertEqual(ollama["restart"], "unless-stopped")
        self.assertIn("ollama", data.get("volumes", {}))
        self.assertEqual(web["environment"]["LLM_PROVIDER"], "${LLM_PROVIDER:-ollama}")
        self.assertEqual(web["environment"]["OLLAMA_BASE_URL"], "${OLLAMA_BASE_URL:-http://ollama:11434}")
        self.assertEqual(web["depends_on"]["ollama"]["condition"], "service_healthy")
        self.assertEqual(web["depends_on"]["ollama-init"]["condition"], "service_completed_successfully")
        self.assertEqual(init["depends_on"]["ollama"]["condition"], "service_healthy")


if __name__ == "__main__":
    unittest.main()
