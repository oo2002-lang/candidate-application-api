"""
Database tables, described as Python classes.

R analogy: think of each class below as the *definition of a data.frame* -- it
lists the columns and their types. A Job object is one row of that data.frame;
a whole table is many rows. `Column(String, ...)` is just saying "this column
holds text", the way a tibble column has type <chr>, <int>, <lgl>, etc.
SQLAlchemy reads these class definitions and runs the CREATE TABLE for you.

Java analogy: these are your JPA/Hibernate @Entity classes -- one class per
table, one Column(...) per field.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    """Current time in UTC. Used as the default timestamp for new rows."""
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"  # the real table name in the database

    # Column(type, ...options) declares a column. This reads much like a set of
    # Java field declarations with annotations.
    id = Column(Integer, primary_key=True)              # auto-incrementing ID
    title = Column(String(200), nullable=False)         # nullable=False -> NOT NULL
    department = Column(String(120), nullable=False)
    description = Column(Text, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)  # is the job open?
    created_at = Column(DateTime, default=utc_now)

    # A convenience link: job.applications gives all applications for this job.
    # Java analogy: like a @OneToMany relationship field.
    applications = relationship("Application", back_populates="job")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    # A foreign key: this column must point to a real jobs.id value.
    # R analogy: job_id is the shared key column you'd join on, e.g.
    #   merge(applications, jobs, by.x="job_id", by.y="id")
    #   dplyr::left_join(applications, jobs, by = c("job_id" = "id"))
    # The ForeignKey just makes the database enforce that the key really exists.
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    candidate_name = Column(String(200), nullable=False)
    email = Column(String(320), nullable=False, index=True)
    # File upload is SIMULATED: we only store the path text, no real file.
    resume_file_path = Column(String(500), nullable=True)   # optional
    cover_letter = Column(Text, nullable=True)              # optional
    submitted_date = Column(DateTime, default=utc_now)

    # The other side of the link: application.job gives the parent Job object.
    job = relationship("Job", back_populates="applications")
