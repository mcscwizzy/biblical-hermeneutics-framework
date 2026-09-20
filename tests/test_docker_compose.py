import unittest
from pathlib import Path

import yaml


class DockerComposeTests(unittest.TestCase):
    def test_default_compose_has_no_runtime_provider_stack(self):
        data = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))

        self.assertIn("services", data)
        self.assertIn("bhf-web", data["services"])
        self.assertNotIn("ollama", data["services"])
        self.assertNotIn("ollama-init", data["services"])
        self.assertNotIn("bhf-https-proxy", data["services"])

        web = data["services"]["bhf-web"]

        self.assertEqual(
            web["environment"]["BHF_ASSISTANT_URL"],
            "${BHF_ASSISTANT_URL:-https://chatgpt.com/g/g-6a36d3641a1c8191afa101ed50a927e9-biblical-hermeneutics-framework-bhf}",
        )
        for key in ("LLM_PROVIDER", "BHF_BASE_URL", "BHF_MODEL", "BHF_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_MODEL"):
            self.assertNotIn(key, web["environment"])
        self.assertNotIn("depends_on", web)
        self.assertEqual(web["ports"], ["${BHF_HTTP_PORT:-8080}:8080"])
        self.assertNotIn("expose", web)

    def test_ollama_runtime_compose_is_removed(self):
        self.assertFalse(Path("docker-compose.ollama.yml").exists())

    def test_reverse_proxy_files_are_not_part_of_the_stack(self):
        self.assertFalse(Path("docker/nginx/Dockerfile").exists())
        self.assertFalse(Path("docker/nginx/local-https.conf").exists())
        self.assertFalse(Path("scripts/generate-local-cert.sh").exists())


if __name__ == "__main__":
    unittest.main()
