"""
Shared test setup ("fixtures").

Java analogy: a pytest fixture is like a @BeforeEach method that BUILDS an object
and hands it to your test. A test just names the fixture as a parameter (e.g.
def test_x(client): ...) and pytest runs the fixture first and passes the result
in. Each test gets a brand-new in-memory database, so tests never interfere.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    # A shared in-memory SQLite DB. StaticPool keeps one connection so all
    # sessions see the same schema/data within a test.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """TestClient wired to the test database via dependency override."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def active_job(db_session):
    job = models.Job(
        title="Senior Backend Engineer",
        department="Engineering",
        description="Build APIs.",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture()
def inactive_job(db_session):
    job = models.Job(
        title="Retired Role",
        department="Operations",
        description="Closed.",
        is_active=False,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job
