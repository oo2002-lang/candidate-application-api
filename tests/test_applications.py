"""
Tests for the application submission logic (POST /api/applications/).

R analogy: this file is a testthat script. Each `def test_...` function is one
`test_that("...", { ... })` block, and `assert x == y` is `expect_equal(x, y)`.
Run them all with `pytest` (the equivalent of `testthat::test_dir()`).

`client` is a fake browser that calls the API in-process (no real server needed)
and hands back the HTTP status code and JSON, so we can check both.
"""


def _payload(job_id, **overrides):
    data = {
        "candidate_name": "Ada Lovelace",
        "email": "ada@example.com",
        "job_id": job_id,
        "resume_file_path": "/uploads/ada_resume.pdf",
        "cover_letter": "I would love to join.",
    }
    data.update(overrides)
    return data


def test_create_application_success(client, active_job):
    resp = client.post("/api/applications/", json=_payload(active_job.id))
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0
    assert body["candidate_name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"
    assert body["job_id"] == active_job.id
    assert body["submitted_date"] is not None


def test_create_application_minimal_optional_fields(client, active_job):
    """resume_file_path and cover_letter are optional."""
    resp = client.post(
        "/api/applications/",
        json={"candidate_name": "Grace Hopper", "email": "grace@example.com", "job_id": active_job.id},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["resume_file_path"] is None
    assert body["cover_letter"] is None


def test_missing_candidate_name_is_rejected(client, active_job):
    resp = client.post("/api/applications/", json={"email": "a@example.com", "job_id": active_job.id})
    assert resp.status_code == 422


def test_empty_candidate_name_is_rejected(client, active_job):
    resp = client.post("/api/applications/", json=_payload(active_job.id, candidate_name=""))
    assert resp.status_code == 422


def test_missing_email_is_rejected(client, active_job):
    resp = client.post(
        "/api/applications/",
        json={"candidate_name": "No Email", "job_id": active_job.id},
    )
    assert resp.status_code == 422


def test_invalid_email_format_is_rejected(client, active_job):
    resp = client.post("/api/applications/", json=_payload(active_job.id, email="not-an-email"))
    assert resp.status_code == 422


def test_missing_job_id_is_rejected(client):
    resp = client.post(
        "/api/applications/",
        json={"candidate_name": "No Job", "email": "nojob@example.com"},
    )
    assert resp.status_code == 422


def test_nonexistent_job_returns_404(client):
    resp = client.post("/api/applications/", json=_payload(999999))
    assert resp.status_code == 404
    assert "does not exist" in resp.json()["detail"]


def test_application_to_inactive_job_is_rejected(client, inactive_job):
    resp = client.post("/api/applications/", json=_payload(inactive_job.id))
    assert resp.status_code == 400
    assert "not accepting" in resp.json()["detail"]


# ---- Bonus: GET /api/applications/{id}/ ----
def test_get_application_by_id(client, active_job):
    created = client.post("/api/applications/", json=_payload(active_job.id)).json()
    resp = client.get(f"/api/applications/{created['id']}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_missing_application_returns_404(client):
    resp = client.get("/api/applications/424242/")
    assert resp.status_code == 404
