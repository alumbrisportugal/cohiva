"""Real HTTPS requests from a disposable container sharing the test TLS network."""

import json
from pathlib import Path

import requests

credentials = json.loads(Path("/data/test-credentials.json").read_text())
base = "https://localhost:18443"
ca = "/tls/caddy/pki/authorities/local/root.crt"
checks = []


def session_for(resident):
    session = requests.Session()
    session.verify = ca
    session.headers["Authorization"] = f"Token {resident['token']}"
    return session


def request(session, method, path, expected=200, **kwargs):
    response = session.request(method, base + path, timeout=45, **kwargs)
    assert response.status_code == expected, (
        method,
        path,
        response.status_code,
        response.text[:200],
    )
    return response


first, second = credentials["residents"][:2]
a, b = session_for(first), session_for(second)
for person, session in ((first, a), (second, b)):
    own = request(session, "GET", f"/api/v1/geno/contract/{person['contract']}/").json()
    assert own["id"] == person["contract"]
    request(session, "GET", "/api/v1/geno/resident-overview/")
request(a, "GET", f"/api/v1/geno/contract/{second['contract']}/", 404)
request(b, "GET", f"/api/v1/geno/rentalunit/{first['unit']}/", 404)
checks.append("two-resident-contract-unit-isolation")
ticket = request(
    a,
    "POST",
    "/api/v1/geno/resident-maintenance/",
    201,
    json={
        "rental_unit": first["unit"],
        "title": "Janela de ensaio",
        "description": "A janela fictícia não fecha corretamente.",
    },
).json()
request(b, "GET", f"/api/v1/geno/resident-maintenance/{ticket['id']}/", 404)
request(
    b,
    "POST",
    "/api/v1/geno/resident-maintenance/",
    400,
    json={
        "rental_unit": first["unit"],
        "title": "Tentativa indevida",
        "description": "Não deve ser possível escrever nesta fração.",
    },
)
comment = request(
    a,
    "POST",
    "/api/v1/geno/resident-maintenance-comments/",
    201,
    json={
        "ticket": ticket["id"],
        "message": "Mensagem fictícia para acompanhamento.",
    },
).json()
request(b, "GET", f"/api/v1/geno/resident-maintenance-comments/{comment['id']}/", 404)
checks.append("maintenance-request-comment-isolation")
# Token authentication applies to DRF; the management HTML additionally requires a session and CSRF.
request(a, "POST", "/geno/living/new/", 403, data={})
checks.append("management-csrf-write-rejection")
print(
    json.dumps(
        {"passed": True, "checks": checks, "tls": "verified using exact staging-local root CA"}
    )
)
