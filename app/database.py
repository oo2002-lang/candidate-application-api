"""
Database setup: how we connect and talk to the database.

R analogy: this is like the top of an R script where you do
    library(DBI)
    con <- dbConnect(RSQLite::SQLite(), "candidates.db")
The "engine" below is that connection. SessionLocal() hands you a short-lived
connection to run one request with (like borrowing a connection from the R
`pool` package, then returning it).

Java analogy: this file is like your JDBC / Hibernate configuration -- it makes
the connection ("engine") and a factory that hands out sessions.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Which database to use. Defaults to a local SQLite file called candidates.db.
# To use PostgreSQL instead, set the DATABASE_URL environment variable to
# something like: postgresql+psycopg://user:pass@localhost/candidates
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./candidates.db")

# SQLite needs one extra flag because the web server uses multiple threads.
# Other databases don't, so we only add it for SQLite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# The "engine" is the actual connection pool to the database.
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# A factory that produces database sessions. Call SessionLocal() to get one.
# (Like calling sessionFactory.openSession() in Hibernate.)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class that all our table classes inherit from.
# Java analogy: think of it like a base @Entity marker that SQLAlchemy uses to
# discover and build your tables.
Base = declarative_base()


def get_db():
    """
    Give one database session to a request, then always close it.

    R analogy: like a helper that does `con <- dbConnect(...)`, lets the caller
    use `con`, and then guarantees `dbDisconnect(con)` runs afterwards (the way
    `on.exit()` cleans up at the end of a function). The `yield` keyword is the
    hand-off point: code before it is setup, code after it is cleanup.

    Java analogy: a try/finally around a connection. FastAPI opens the session
    before the endpoint runs and closes it after the response is sent.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
