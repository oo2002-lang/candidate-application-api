"""
Load some sample jobs so the API has data to show.

R analogy: this is like building a small data.frame of example rows and writing
it to the database, e.g.
    jobs <- data.frame(title=..., department=..., is_active=...)
    DBI::dbWriteTable(con, "jobs", jobs, append = TRUE)
The list of tuples below is that data.frame; the loop is the dbWriteTable.

Run it with:  python -m app.seed
"""
from app.database import Base, SessionLocal, engine
from app import models

# Each tuple is: (title, department, description, is_active)
SAMPLE_JOBS = [
    ("Senior Backend Engineer", "Engineering", "Build and scale our Python APIs.", True),
    ("Frontend Engineer", "Engineering", "Craft delightful React interfaces.", True),
    ("Product Designer", "Design", "Own the end-to-end design process.", True),
    ("Data Analyst", "Analytics", "Turn data into decisions.", True),
    ("Office Manager", "Operations", "This role has already been filled.", False),
]


def seed():
    # Make sure the tables exist first.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Don't double-seed if jobs are already there.
        if db.query(models.Job).count() > 0:
            print("Jobs already exist - skipping seed.")
            return

        # Add each sample job one at a time (a plain loop, easy to follow).
        for title, department, description, is_active in SAMPLE_JOBS:
            job = models.Job(
                title=title,
                department=department,
                description=description,
                is_active=is_active,
            )
            db.add(job)

        db.commit()  # write them all to the database
        print(f"Seeded {len(SAMPLE_JOBS)} jobs.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
