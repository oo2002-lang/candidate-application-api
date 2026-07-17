"""
Schemas: the SHAPE of the JSON going in and coming out of the API.

R analogy: these classes do the job of the checks you'd write at the top of a
function to guard your inputs, e.g.
    stopifnot(is.character(candidate_name), nchar(candidate_name) > 0)
    if (!grepl("@", email)) stop("bad email")
...except you declare the rules once as types and Pydantic enforces them
automatically. If the incoming JSON breaks a rule, the request is rejected with
a 422 error BEFORE your endpoint code runs -- you never see bad data. It's the
same idea as the `checkmate` package (assert_string, assert_int) or plumber's
argument coercion.

Java analogy: these are DTOs with Bean Validation annotations (@NotNull,
@Email, @Size) baked into the field types.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- What we SEND BACK for a job ----------
class JobOut(BaseModel):
    # from_attributes=True lets Pydantic read values straight off a Job database
    # object (job.title, job.department, ...) when building the JSON response.
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    department: str
    description: str
    is_active: bool
    created_at: datetime


# ---------- The paginated list wrapper for GET /api/jobs/ ----------
class PaginatedJobs(BaseModel):
    total: int          # how many active jobs exist in total
    limit: int          # page size that was used
    offset: int         # how many were skipped
    items: list[JobOut]  # this page of jobs


# ---------- What we ACCEPT when creating an application ----------
class ApplicationCreate(BaseModel):
    # These three are REQUIRED. "..." means "no default -> required".
    # min_length=1 rejects an empty name; EmailStr rejects a malformed email.
    candidate_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    job_id: int = Field(..., gt=0)   # gt=0 -> must be greater than 0

    # These two are OPTIONAL (default None means "not provided is fine").
    resume_file_path: str | None = Field(default=None, max_length=500)
    cover_letter: str | None = None


# ---------- What we SEND BACK for an application ----------
class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    candidate_name: str
    email: EmailStr
    resume_file_path: str | None
    cover_letter: str | None
    submitted_date: datetime
