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
        self.assertIn("bhf-https-proxy", data["services"])

        ollama = data["services"]["ollama"]
        init = data["services"]["ollama-init"]
        web = data["services"]["bhf-web"]
        proxy = data["services"]["bhf-https-proxy"]

        self.assertEqual(ollama["image"], "ollama/ollama:latest")
        self.assertEqual(ollama["ports"], ["11434:11434"])
        self.assertEqual(ollama["restart"], "unless-stopped")
        self.assertIn("ollama", data.get("volumes", {}))
        self.assertEqual(web["environment"]["LLM_PROVIDER"], "${LLM_PROVIDER:-ollama}")
        self.assertEqual(web["environment"]["OLLAMA_BASE_URL"], "${OLLAMA_BASE_URL:-http://ollama:11434}")
        self.assertEqual(web["depends_on"]["ollama"]["condition"], "service_healthy")
        self.assertEqual(web["depends_on"]["ollama-init"]["condition"], "service_completed_successfully")
        self.assertEqual(init["depends_on"]["ollama"]["condition"], "service_healthy")
        self.assertEqual(proxy["image"], "nginx:1.27-alpine")
        self.assertEqual(proxy["ports"], ["${BHF_HTTPS_PORT:-8443}:443"])
        self.assertEqual(proxy["depends_on"]["bhf-web"]["condition"], "service_healthy")
        self.assertIn("./docker/nginx/local-https.conf:/etc/nginx/conf.d/default.conf:ro", proxy["volumes"])
        self.assertIn("./.bhf/certs:/etc/nginx/certs:ro", proxy["volumes"])

    def test_https_nginx_config_proxies_to_web_app(self):
        config = Path("docker/nginx/local-https.conf").read_text(encoding="utf-8")

        self.assertIn("listen 443 ssl;", config)
        self.assertIn("ssl_certificate /etc/nginx/certs/localhost.crt;", config)
        self.assertIn("ssl_certificate_key /etc/nginx/certs/localhost.key;", config)
        self.assertIn("proxy_pass http://bhf-web:8080;", config)
        self.assertIn("proxy_set_header X-Forwarded-Proto https;", config)
        self.assertIn("proxy_set_header Upgrade $http_upgrade;", config)
        self.assertIn("proxy_set_header Connection $connection_upgrade;", config)


if __name__ == "__main__":
    unittest.main()
