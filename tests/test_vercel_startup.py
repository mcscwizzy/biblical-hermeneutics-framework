import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _vercel_python(command: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith("BHF_"):
            environment.pop(name)
    environment["VERCEL"] = "1"
    return subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def test_vercel_can_import_constructed_fastapi_app():
    result = _vercel_python(
        "from bhf_web.app import app; "
        "assert app.title == 'BHF Bible Reader'; "
        "print(type(app).__name__)"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "FastAPI"


def test_vercel_health_endpoint_returns_expected_payload():
    result = _vercel_python(
        "import asyncio\n"
        "import httpx\n"
        "from bhf_web.app import app\n"
        "async def check_health():\n"
        "    transport = httpx.ASGITransport(app=app)\n"
        "    async with httpx.AsyncClient(\n"
        "        transport=transport, base_url='http://test'\n"
        "    ) as client:\n"
        "        response = await client.get('/api/health')\n"
        "    assert response.status_code == 200\n"
        "    assert response.json() == {'status': 'ok', 'service': 'bhf-web'}\n"
        "asyncio.run(check_health())"
    )

    assert result.returncode == 0, result.stderr
