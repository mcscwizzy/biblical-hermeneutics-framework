import json
import time

import requests


def test_genesis_projection_endpoint_samples(base_url):
    samples = []
    for _ in range(3):
        start = time.monotonic()
        response = requests.get(f"{base_url}/api/narrative-explorer/v1/passages/Genesis/1", params={"verse_start": 1, "verse_end": 5}, timeout=90)
        elapsed = (time.monotonic() - start) * 1000
        assert response.status_code == 200
        assert response.json()["passage"]["reference"] == "Genesis 1:1-5"
        samples.append({"elapsed_ms": round(elapsed, 1), "bytes": len(response.content)})
    print("NE11D3_ENDPOINT=" + json.dumps(samples), flush=True)
