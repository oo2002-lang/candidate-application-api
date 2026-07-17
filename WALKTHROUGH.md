# Interview Walkthrough

A plain-English guide to this project, written so you can **explain and defend it**
in an interview. It leans on Java/Processing analogies, since that's your strong
suit. Read this top-to-bottom once and you'll be able to talk through any part.

---

## 1. The 30-second summary (say this first)

> "It's a small REST API for a job-application system, built with **FastAPI** and
> **SQLAlchemy** on top of SQLite. There are two tables — `Job` and `Application`
> — and three endpoints: list open jobs, submit an application, and fetch a single
> application. Input validation is handled by Pydantic schemas, and I wrote 16
> unit tests covering the happy paths and every validation rule."

That sentence alone answers "walk me through your project."

---

## 2. The mental model (map it to what you already know)

FastAPI is structured very much like **Java Spring Boot**. If you can read a Spring
`@RestController`, you can read this.

| This project (Python/FastAPI) | Java equivalent you know |
|---|---|
| `@app.get("/api/jobs/")` above a function | `@GetMapping("/api/jobs/")` on a method |
| `@app.post(...)` | `@PostMapping(...)` |
| A function under a decorator | A controller method |
| `models.py` classes (`Job`, `Application`) | JPA `@Entity` classes |
| `Column(String(200), nullable=False)` | a field with `@Column(nullable=false)` |
| `schemas.py` classes | DTOs (Data Transfer Objects) |
| Pydantic `EmailStr`, `Field(min_length=1)` | Bean Validation `@Email`, `@Size` |
| `Depends(get_db)` | `@Autowired` dependency injection |
| `db.query(Job)...` | Hibernate / JPA repository query |
| SQLAlchemy | Hibernate (the ORM) |
| `raise HTTPException(status_code=404)` | `throw new ResponseStatusException(NOT_FOUND)` |
| pytest fixture | JUnit `@BeforeEach` setup method |

> **ORM** = Object-Relational Mapper. It lets you work with database rows as
> objects (`job.title`) instead of writing raw SQL. Hibernate does this in Java;
> SQLAlchemy does it here.

---

## 3. What each file does (the tour)

```
app/
  database.py   -> how we connect to the DB (like JDBC/Hibernate config)
  models.py     -> the two tables as classes (like @Entity classes)
  schemas.py    -> the shapes of JSON in/out + validation (like DTOs)
  main.py       -> the app + all 3 endpoints (like a @RestController)
  seed.py       -> loads 5 sample jobs so there's data to show
tests/
  conftest.py            -> test setup (fresh in-memory DB per test)
  test_jobs.py           -> tests for listing/pagination
  test_applications.py   -> tests for submitting + validation
```

**Why this split?** Separation of concerns. The database shape (`models`) is kept
separate from the API's public contract (`schemas`). That means I can change a
column name internally without breaking the JSON that clients depend on — the same
reason you use DTOs instead of exposing entities directly in Java.

---

## 4. The two tables (data model)

**Job**: `id`, `title`, `department`, `description`, `is_active`, `created_at`
**Application**: `id`, `job_id` (foreign key → Job), `candidate_name`, `email`,
`resume_file_path`, `cover_letter`, `submitted_date`

Talking points:
- **`is_active` on Job** — the spec says list *active* jobs, so I added a boolean
  flag rather than deleting closed jobs. It also lets me block applications to a
  closed job. (Soft-state instead of hard-delete.)
- **`job_id` foreign key** — this is the relationship. One Job has many
  Applications (one-to-many). The database enforces that an application must point
  to a real job.
- **`resume_file_path` is just a string** — the spec said to *simulate* file
  upload, so I store the path text and don't touch the filesystem. I'd call this
  out as a deliberate scope decision.

---

## 5. Walk through each endpoint (this is what they'll ask)

### `GET /api/jobs/` — list open jobs

1. Request comes in, optionally with `?limit=10&offset=0`.
2. `limit`/`offset` are validated (limit 1–100, offset ≥ 0) — bad values → **422**.
3. Query: "select jobs where `is_active` is true", newest first.
4. `total` = count of all active jobs; then apply `LIMIT`/`OFFSET` for this page.
5. Return `{ total, limit, offset, items: [...] }`.

**Why the envelope (total/limit/offset)?** So the client knows how many pages
exist. Returning a bare list gives no way to build "page 2 of 5". That's the
**pagination bonus**.

### `POST /api/applications/` — submit an application

1. The JSON body is validated against `ApplicationCreate` **before my code runs**:
   - `candidate_name`, `email`, `job_id` required → missing = **422**
   - `email` must be a valid email format → bad = **422**
   - empty name → **422**
2. My code then checks the *business* rules:
   - job doesn't exist → **404**
   - job exists but is closed → **400**
3. If all good: build the `Application` row, save it, return it with **201 Created**.

**Key point to make:** there are *two layers* of validation. Pydantic handles
**shape/format** (is this well-formed?); my endpoint handles **business rules**
(does this job exist and is it open?). That separation is intentional.

### `GET /api/applications/{id}/` — fetch one application (bonus)

1. Look up by id.
2. Found → return it (**200**). Not found → **404**.

---

## 6. Validation & status codes (have this table ready)

| Situation | Status | Who enforces it |
|---|---|---|
| Missing required field | 422 | Pydantic schema |
| Malformed email | 422 | Pydantic `EmailStr` |
| Empty candidate name | 422 | Pydantic `min_length=1` |
| Bad pagination value | 422 | FastAPI `Query(ge=, le=)` |
| Job id doesn't exist | 404 | my endpoint code |
| Job is closed | 400 | my endpoint code |
| Application id not found | 404 | my endpoint code |
| Successful create | 201 | endpoint |

**Why 404 vs 400 vs 422?**
- **422** = you sent malformed data (wrong shape/format).
- **404** = the thing you referenced doesn't exist.
- **400** = the data is well-formed and the target exists, but the request breaks a
  rule (applying to a closed job).

Using the right status codes is a core part of "REST principles," which is exactly
what they said they're assessing.

---

## 7. Testing approach (they explicitly assess this)

- **16 tests**, run with `pytest -q`.
- Each test gets a **fresh in-memory SQLite database** (see `conftest.py`), so
  tests are isolated and never depend on each other or leave data behind.
- I use FastAPI's `TestClient` to send real HTTP requests to the app in-process —
  no server needed. (Like Spring's `MockMvc`.)
- Coverage: successful submission, each required-field-missing case, invalid email,
  empty name, nonexistent job (404), closed job (400), both bonus lookups, and
  pagination (page size, offset paging, active-only filtering, bad params).

If asked "what would you add with more time?": integration tests against real
Postgres, and a test for duplicate applications.

---

## 8. Likely interview questions + short answers

**Q: Why FastAPI over Django?**
A: For a small, focused JSON API it's lighter and the validation + auto-generated
docs come built in. Django REST Framework would also be a fine choice; it shines
when you also want an admin panel and a bigger framework around it.

**Q: What is Pydantic doing?**
A: It defines the expected shape of the JSON and validates it automatically. If the
body doesn't match, FastAPI returns a 422 with a clear error before my code runs.
It's like Bean Validation annotations in Java, but the type *is* the contract.

**Q: What does `Depends(get_db)` do?**
A: Dependency injection. FastAPI calls `get_db`, which opens a database session,
hands it to my function, and closes it afterward — so each request gets its own
session and I never leak connections. Same idea as `@Autowired` + a try/finally.

**Q: How does the ORM save a row?**
A: `db.add(obj)` stages it, `db.commit()` writes it, `db.refresh(obj)` reloads it
so I get the DB-generated `id` and timestamp back.

**Q: Why keep `schemas` separate from `models`?**
A: The database shape and the public API contract are different concerns. DTOs vs
entities. It lets each evolve independently and avoids leaking internal columns.

**Q: Is it production-ready?**
A: The structure is, but I'd add: Alembic migrations instead of auto-creating
tables, real file storage for resumes, authentication, rate limiting, and I'd run
it on Postgres. I noted the Postgres switch is one environment variable.

**Q: How would you switch to PostgreSQL?**
A: Set `DATABASE_URL` to a Postgres connection string and install the driver. No
code changes — `database.py` reads that variable. SQLAlchemy handles the rest.

---

## 9. How to run it live (for a demo)

```powershell
cd "C:\Users\thegr\OneDrive\Desktop\candidate-application-api"
.venv\Scripts\activate
python -m app.seed              # load sample jobs
uvicorn app.main:app --reload   # start the server
```

Then open **http://127.0.0.1:8000/docs** — an interactive page where you can click
each endpoint and send real requests. Great for a live demo: show `GET /api/jobs/`,
then `POST /api/applications/` with a bad email (watch the 422), then a good one
(watch the 201).

Run the tests with:

```powershell
pytest -q
```

---

## 10. One honest caveat to mention if asked about setup

Your machine runs Python 3.14, which is newer than some libraries' prebuilt
packages. I installed with `pip install --only-binary=:all: -r requirements.txt`
so pip uses prebuilt wheels instead of trying (and failing) to compile Pydantic
from source. On a normal Python 3.11/3.12 machine a plain `pip install` just works.
Mentioning this shows you understood the actual failure, not just that "it broke."
