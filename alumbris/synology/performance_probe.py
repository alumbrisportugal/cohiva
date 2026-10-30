"""Sequential staging latency sample, not a load/capacity certification."""

import json
import statistics
import time
from pathlib import Path

import requests

resident = json.loads(Path("/data/test-credentials.json").read_text())["residents"][0]
session = requests.Session()
session.verify = "/tls/caddy/pki/authorities/local/root.crt"
session.headers["Authorization"] = f"Token {resident['token']}"
url = f"https://localhost:18443/api/v1/geno/contract/{resident['contract']}/"
samples = []
for _ in range(20):
    start = time.perf_counter()
    response = session.get(url, timeout=20)
    assert response.status_code == 200
    assert response.json()["id"] == resident["contract"]
    samples.append((time.perf_counter() - start) * 1000)
ordered = sorted(samples)
print(
    json.dumps(
        {
            "requests": len(samples),
            "successes": len(samples),
            "concurrency": 1,
            "median_ms": round(statistics.median(samples), 2),
            "p95_ms": round(ordered[18], 2),
            "max_ms": round(max(samples), 2),
            "scope": "authenticated contract read, sequential sample only",
        }
    )
)
