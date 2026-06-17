from fastapi.testclient import TestClient

from main import app


def test_health_get():
    with TestClient(app) as c:
        res = c.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_head():
    with TestClient(app) as c:
        res = c.head("/health")
    assert res.status_code == 200
