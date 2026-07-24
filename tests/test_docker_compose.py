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
        self.assertEqual(web["expose"], ["8080"])
        self.assertNotIn("ports", web)
        self.assertEqual(init["depends_on"]["ollama"]["condition"], "service_healthy")
        self.assertEqual(proxy["image"], "bhf-https-proxy:local")
        self.assertEqual(proxy["build"]["context"], ".")
        self.assertEqual(proxy["build"]["dockerfile"], "docker/nginx/Dockerfile")
        self.assertEqual(proxy["ports"], ["${BHF_HTTPS_PORT:-8080}:443"])
        self.assertEqual(proxy["depends_on"]["bhf-web"]["condition"], "service_healthy")
        self.assertNotIn("volumes", proxy)

    def test_https_nginx_config_proxies_to_web_app(self):
        config = Path("docker/nginx/local-https.conf").read_text(encoding="utf-8")

        self.assertIn("listen 443 ssl;", config)
        self.assertIn("ssl_certificate /etc/nginx/certs/localhost.crt;", config)
        self.assertIn("ssl_certificate_key /etc/nginx/certs/localhost.key;", config)
        self.assertIn("proxy_pass http://bhf-web:8080;", config)
        self.assertIn("proxy_set_header X-Forwarded-Proto https;", config)
        self.assertIn("proxy_set_header Upgrade $http_upgrade;", config)
        self.assertIn("proxy_set_header Connection $connection_upgrade;", config)

    def test_https_nginx_image_generates_local_cert_files(self):
        dockerfile = Path("docker/nginx/Dockerfile").read_text(encoding="utf-8")

        self.assertIn("FROM nginx:1.27-alpine AS certs", dockerfile)
        self.assertIn("apk add --no-cache openssl", dockerfile)
        self.assertIn('-subj "/CN=localhost"', dockerfile)
        self.assertIn('subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1', dockerfile)
        self.assertIn("COPY docker/nginx/local-https.conf /etc/nginx/conf.d/default.conf", dockerfile)
        self.assertIn("COPY --from=certs /etc/nginx/certs/localhost.crt /etc/nginx/certs/localhost.crt", dockerfile)
        self.assertIn("COPY --from=certs /etc/nginx/certs/localhost.key /etc/nginx/certs/localhost.key", dockerfile)


if __name__ == "__main__":
    unittest.main()
