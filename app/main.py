"""
The web application and all of its endpoints.

R analogy: if you've used the `plumber` package, this file IS a plumber API.
In plumber you write a normal function and tag it with a special comment:
    #* @get /api/jobs
    function() { ... return a data.frame ... }
Here the tag is `@app.get("/api/jobs/")` written ABOVE the function instead of
in a comment. Same idea in both: "when a request hits this URL, run this
function, and whatever the function returns becomes the JSON response."
The `@` line is called a *decorator* -- read it as plumber's `#*` annotation.

Java analogy: this file is a Spring @RestController. @app.get / @app.post are
the equivalents of @GetMapping / @PostMapping.
"""
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, engine, get_db

# Create the database tables from our model classes if they don't exist yet.
# (In a big project a migration tool like Alembic/Flyway would do this instead.)
Base.metadata.create_all(bind=engine)

# The application object. Title/description/version show up in the auto-generated
# API docs at /docs.
app = FastAPI(
    title="Candidate Application API",
    description="A simple REST API for submitting job applications.",
    version="1.0.0",
)


@app.get("/")
def root():
    """Health check. Confirms the server is up and points to the docs."""
    return {"status": "ok", "docs": "/docs"}


# ---------------------------------------------------------------------------
# GET /api/jobs/  -> list the active (open) jobs, one page at a time
# ---------------------------------------------------------------------------
@app.get("/api/jobs/", response_model=schemas.PaginatedJobs)
def list_jobs(
    # These two come from the URL query string, e.g. /api/jobs/?limit=10&offset=0
    # ge/le are "greater-or-equal"/"less-or-equal" bounds -> a bad value is a 422.
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    # Depends(get_db) injects a database session (see get_db in database.py).
    # Java analogy: constructor/field @Autowired dependency injection.
    db: Session = Depends(get_db),
):
    """Return active job openings, newest first, with pagination info."""
    # Build a query for active jobs only. This is the ORM equivalent of
    # SELECT * FROM jobs WHERE is_active = true.
    # R analogy: subset(jobs, is_active == TRUE)  /  filter(jobs, is_active)
    # Note the query is LAZY -- nothing runs until .all()/.count() below, just
    # like a dbplyr pipeline only hits the database when you call collect().
    query = db.query(models.Job).filter(models.Job.is_active == True)  # noqa: E712

    total = query.count()  # how many active jobs there are in total
    # R analogy for the three lines below: sort newest-first, then keep one
    # "page" of rows -- like head(arrange(jobs, desc(created_at)), limit) after
    # dropping the first `offset` rows. .all() is the collect() that finally
    # fetches the rows into memory.
    jobs = (
        query.order_by(models.Job.created_at.desc(), models.Job.id.desc())
        .limit(limit)     # take at most `limit` rows  (SQL LIMIT)
        .offset(offset)   # skip the first `offset` rows (SQL OFFSET)
        .all()
    )

    # FastAPI turns this object into JSON automatically, using the JobOut/
    # PaginatedJobs schemas as the template.
    return schemas.PaginatedJobs(total=total, limit=limit, offset=offset, items=jobs)


# ---------------------------------------------------------------------------
# POST /api/applications/  -> submit a new application
# ---------------------------------------------------------------------------
# status_code=201 means "Created" -- the correct REST response for making a
# new resource.
@app.post("/api/applications/", response_model=schemas.ApplicationOut, status_code=201)
def create_application(
    # `payload` is the JSON body, already validated against ApplicationCreate.
    # If required fields are missing or the email is malformed, FastAPI has
    # ALREADY rejected the request with a 422 before we get here.
    payload: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
):
    """Validate the referenced job, then create and save the application."""
    # Look up the job by primary key (SELECT * FROM jobs WHERE id = ?).
    job = db.get(models.Job, payload.job_id)

    # Rule 1: the job must exist.  raise HTTPException == send an error response.
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job with id {payload.job_id} does not exist.",
        )
    # Rule 2: you can't apply to a job that's been closed.
    if not job.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Job with id {payload.job_id} is not accepting applications.",
        )

    # Build the row object from the incoming data...
    application = models.Application(
        job_id=payload.job_id,
        candidate_name=payload.candidate_name.strip(),
        email=str(payload.email),
        resume_file_path=payload.resume_file_path,
        cover_letter=payload.cover_letter,
    )
    # ...then save it. add = stage it, commit = write to DB, refresh = reload it
    # so we get the database-assigned id and submitted_date back.
    db.add(application)
    db.commit()
    db.refresh(application)

    return application


# ---------------------------------------------------------------------------
# GET /api/applications/{id}/  -> fetch one application by its id (bonus)
# ---------------------------------------------------------------------------
@app.get("/api/applications/{application_id}/", response_model=schemas.ApplicationOut)
def get_application(application_id: int, db: Session = Depends(get_db)):
    """Return a single application, or 404 if that id doesn't exist."""
    application = db.get(models.Application, application_id)
    if application is None:
        raise HTTPException(
            status_code=404,
            detail=f"Application with id {application_id} not found.",
        )
    return application
