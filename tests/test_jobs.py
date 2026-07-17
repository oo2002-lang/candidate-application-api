"""Tests for GET /api/jobs/ (listing, active-only filtering, pagination)."""
from app import models


def _make_jobs(db_session, active_count, inactive_count=0):
    for i in range(active_count):
        db_session.add(models.Job(title=f"Active {i}", department="Eng", description="", is_active=True))
    for i in range(inactive_count):
        db_session.add(models.Job(title=f"Inactive {i}", department="Ops", description="", is_active=False))
    db_session.commit()


def test_list_jobs_returns_only_active(client, db_session):
    _make_jobs(db_session, active_count=3, inactive_count=2)
    resp = client.get("/api/jobs/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert all(job["is_active"] for job in body["items"])


def test_list_jobs_empty(client):
    resp = client.get("/api/jobs/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_pagination_limits_page_size(client, db_session):
    _make_jobs(db_session, active_count=5)
    resp = client.get("/api/jobs/?limit=2&offset=0")
    body = resp.json()
    assert body["total"] == 5  # total reflects all active jobs
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0


def test_pagination_offset_walks_the_list(client, db_session):
    _make_jobs(db_session, active_count=5)
    page1 = client.get("/api/jobs/?limit=2&offset=0").json()
    page2 = client.get("/api/jobs/?limit=2&offset=2").json()
    ids_page1 = {j["id"] for j in page1["items"]}
    ids_page2 = {j["id"] for j in page2["items"]}
    assert ids_page1.isdisjoint(ids_page2)  # no overlap between pages


def test_invalid_pagination_params_rejected(client):
    assert client.get("/api/jobs/?limit=0").status_code == 422
    assert client.get("/api/jobs/?limit=1000").status_code == 422
    assert client.get("/api/jobs/?offset=-1").status_code == 422
