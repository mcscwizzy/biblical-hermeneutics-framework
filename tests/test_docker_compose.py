import unittest
from pathlib import Path

import yaml


class DockerComposeTests(unittest.TestCase):
    def test_default_compose_uses_openrouter_without_ollama_services(self):
        data = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

        self.assertIn("services", data)
        self.assertIn("bhf-web", data["services"])
        self.assertNotIn("ollama", data["services"])
        self.assertNotIn("ollama-init", data["services"])
        self.assertNotIn("bhf-https-proxy", data["services"])

        web = data["services"]["bhf-web"]

        self.assertEqual(web["environment"]["LLM_PROVIDER"], "${LLM_PROVIDER:-openrouter}")
        self.assertEqual(web["environment"]["BHF_BASE_URL"], "${BHF_BASE_URL:-https://openrouter.ai/api/v1}")
        self.assertEqual(web["environment"]["BHF_MODEL"], "${BHF_MODEL:-openrouter/free}")
        self.assertNotIn("depends_on", web)
        self.assertEqual(web["ports"], ["${BHF_HTTP_PORT:-8080}:8080"])
        self.assertNotIn("expose", web)

    def test_ollama_compose_keeps_the_opt_in_local_stack(self):
        data = yaml.safe_load(Path("docker-compose.ollama.yml").read_text(encoding="utf-8"))

        self.assertIn("ollama", data["services"])
        self.assertIn("ollama-init", data["services"])
        self.assertIn("bhf-web", data["services"])
        self.assertIn("ollama", data.get("volumes", {}))

        ollama = data["services"]["ollama"]
        init = data["services"]["ollama-init"]
        web = data["services"]["bhf-web"]

        self.assertEqual(ollama["image"], "ollama/ollama:latest")
        self.assertEqual(ollama["ports"], ["11434:11434"])
        self.assertEqual(ollama["restart"], "unless-stopped")
        self.assertEqual(web["environment"]["LLM_PROVIDER"], "ollama")
        self.assertEqual(web["environment"]["OLLAMA_BASE_URL"], "${OLLAMA_BASE_URL:-http://ollama:11434}")
        self.assertEqual(web["depends_on"]["ollama"]["condition"], "service_healthy")
        self.assertEqual(web["depends_on"]["ollama-init"]["condition"], "service_completed_successfully")
        self.assertEqual(init["depends_on"]["ollama"]["condition"], "service_healthy")

    def test_reverse_proxy_files_are_not_part_of_the_stack(self):
        self.assertFalse(Path("docker/nginx/Dockerfile").exists())
        self.assertFalse(Path("docker/nginx/local-https.conf").exists())
        self.assertFalse(Path("scripts/generate-local-cert.sh").exists())


if __name__ == "__main__":
    unittest.main()
