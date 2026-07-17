# Candidate Application API — my notes

These are my own notes on this project: what it is, how the pieces fit, and how
I run it. It's written to me, in plain terms, leaning on R (and a bit of Java)
since that's what I already know. For the deeper "explain and defend it in an
interview" version, I keep [`WALKTHROUGH.md`](WALKTHROUGH.md).

## What I built

A small REST API for a job-application system. Two tables and three endpoints:

| Endpoint | Method | What it does |
|---|---|---|
| `/api/jobs/` | `GET` | List the open jobs (paginated) |
| `/api/applications/` | `POST` | Submit an application (validated) |
| `/api/applications/{id}/` | `GET` | Fetch one application |

Built with **FastAPI** (the web framework), **SQLAlchemy** (the database layer),
and **SQLite** (the database file). When it's running, `/docs` gives me a
clickable page to try every endpoint.

## How to think about it (in R terms)

The closest R thing to this whole project is the **`plumber`** package. If I've
written a plumber API, I already get the shape of this:

| What I know in R | Same idea here |
|---|---|
| `#* @get /jobs` above a function | `@app.get("/api/jobs/")` above a function ([`main.py`](app/main.py)) |
| a function that returns a `data.frame`/`list` | a function that returns an object → becomes JSON |
| a `data.frame` / `tibble` (a table) | a *class* in [`models.py`](app/models.py); each row is one object |
| `filter(jobs, is_active)` / `subset(...)` | `db.query(Job).filter(Job.is_active == True)` |
| `head(arrange(df, desc(x)), n)` | `.order_by(...).limit(n).offset(k)` |
| `stopifnot(...)` / `checkmate::assert_*` | the schema classes in [`schemas.py`](app/schemas.py) |
| `DBI::dbConnect(...)` | the "engine" in [`database.py`](app/database.py) |
| `testthat::test_that()` + `expect_equal()` | `def test_...` + `assert` in [`tests/`](tests) |

Three Python things that look weird coming from R:
- **`@something` on the line above a function** is a *decorator* — read it like
  plumber's `#*` tag: "attach this to the function below."
- **`def foo(x):`** defines a function; indentation marks the body (no `{ }`).
- **`self`** is just "this object" — I can mostly skim past it when reading.

## Where everything lives

```
app/
  database.py   -> how I connect to the DB      (like DBI::dbConnect)
  models.py     -> the two tables as classes     (like defining a data.frame)
  schemas.py    -> the JSON in/out + validation  (like stopifnot on inputs)
  main.py       -> the app + all 3 endpoints     (like a plumber API file)
  seed.py       -> loads 5 sample jobs so there's data to see
tests/
  conftest.py            -> test setup (a fresh in-memory DB per test)
  test_jobs.py           -> tests for listing + pagination
  test_applications.py   -> tests for submitting + validation
```

Best order to read the files, because each builds on the last:
`database.py` → `models.py` → `schemas.py` → `main.py`.

Every file also opens with a comment block explaining it in R (and Java) terms.

**Why `models` and `schemas` are separate:** `models` is the database shape;
`schemas` is what the API accepts and returns. Keeping them apart means I can
rename a database column without breaking the JSON that callers rely on.

## The two tables

**Job**: `id`, `title`, `department`, `description`, `is_active`, `created_at`
**Application**: `id`, `job_id` (points at a Job), `candidate_name`, `email`,
`resume_file_path`, `cover_letter`, `submitted_date`

Decisions I made:
- **`is_active`** — the task says list *active* jobs, so I flag them instead of
  deleting closed ones. It also lets me block applications to a closed job.
- **`job_id`** is the link between the tables (one job → many applications), the
  same key I'd join on with `merge()` / `left_join()`. The database makes sure it
  points at a real job.
- **`resume_file_path` is just a string** — the task said to *simulate* the file
  upload, so I store the path text and never touch the filesystem. Deliberate.

## How I run it

```powershell
# one-time setup
python -m venv .venv
.venv\Scripts\activate
pip install --only-binary=:all: -r requirements.txt

# run it
python -m app.seed              # optional: load 5 sample jobs
uvicorn app.main:app --reload   # start the server
```

Then open **http://127.0.0.1:8000/docs** and click through the endpoints.
`Ctrl+C` in the terminal stops the server.

> The `--only-binary=:all:` flag matters on my machine: I'm on Python 3.14, which
> is newer than some libraries' prebuilt packages, so this forces pip to grab
> prebuilt wheels instead of trying (and failing) to compile Pydantic from source.

## How I test it

```powershell
pytest -q
```

16 tests, each on its own fresh in-memory database. They cover a successful
submission, every validation rule (missing fields, bad email, empty name),
a nonexistent job (404), a closed job (400), both bonus lookups, and pagination.

## Validation & status codes (what returns what)

| Situation | Status | Who catches it |
|---|---|---|
| Missing `candidate_name` / `email` / `job_id` | 422 | the schema (`schemas.py`) |
| Malformed email | 422 | the schema (`EmailStr`) |
| Empty candidate name | 422 | the schema (`min_length=1`) |
| Bad `limit`/`offset` | 422 | FastAPI `Query(ge=, le=)` |
| Job id doesn't exist | 404 | my endpoint code |
| Job is closed | 400 | my endpoint code |
| Application id not found | 404 | my endpoint code |
| Successful create | 201 | the endpoint |

Quick rule of thumb: **422** = the data I sent is the wrong shape/format;
**404** = the thing I pointed at doesn't exist; **400** = well-formed and it
exists, but it breaks a rule (applying to a closed job).

## If I ever move it to PostgreSQL

```powershell
pip install "psycopg[binary]"
$env:DATABASE_URL = "postgresql+psycopg://user:pass@localhost:5432/candidates"
uvicorn app.main:app
```

No code changes — [`database.py`](app/database.py) reads `DATABASE_URL` and only
adds the SQLite-specific setting when the URL is SQLite.
