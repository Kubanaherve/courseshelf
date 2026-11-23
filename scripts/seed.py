#!/usr/bin/env python3
"""I load my demonstration accounts, editions, copies, and one finished loan.

I reserve the lender's copy, I confirm pickup, and I confirm the return, all
inside one database transaction. I leave a second copy on loan so my shelf
shows a return-by date. I refuse to run this when I set APP_ENV=production.
"""

import json
import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import load_environment
from app.core import (
    BORROWER_EMAIL,
    DEMO_COURSES,
    DEMO_LANDMARKS,
    LENDER_EMAIL,
    campus_today,
    hash_password,
    transaction,
)
from app.loans import confirm_pickup, confirm_return, reserve_copy
from app.openlibrary import lookup_isbn, map_record

CORE_ISBNS = ("9780132350884", "9780262033848")

# Real Open Library editions. Each note is the lender's own words, under 280 characters.
EXTRA_COPIES = (
    ("9780134685991", "lender", "DEMO-CS101", 0, "I kept Joshua Bloch's Effective Java for the CS101 practical on equals and hashCode. This is the real third-edition cover. Collect it at the library steps and bring it back before Tuesday. Please do not write in it."),
    ("9780201633610", "lender", "DEMO-WD301", 1, "This is the Gang of Four book, Design Patterns, by Gamma, Helm, Johnson, and Vlissides. I used the observer and strategy chapters in the web workshop. It sits on the lab block bench. The cover is the real one."),
    ("9781449373320", "lender", "DEMO-DS201", 2, "Martin Kleppmann's Designing Data-Intensive Applications. I read the replication chapter before the data structures session. Pickup is the student hub desk. Search for Kleppmann or replication and this card appears."),
    ("9780134494166", "lender", "DEMO-WD301", 2, "Robert C. Martin's Clean Architecture, a different book from Clean Code. I used the dependency-rule pages while naming my Flask routes. Pickup is the student hub desk. Leave the Clean Code card for the demo."),
    ("9781492078005", "lender", "DEMO-WD301", 1, "Eric Freeman's Head First Design Patterns. The adapter and decorator chapters are the ones I marked with a paper slip, not a pen. It is on the lab block bench for the web workshop."),
    ("9780134757599", "lender", "DEMO-CS101", 0, "Martin Fowler's Refactoring. I used the chapter on extracting functions while cleaning the loan code. Library steps, north side. The cover is the real edition image from Open Library."),
    ("9780596517748", "lender", "DEMO-WD301", 2, "Douglas Crockford's JavaScript: The Good Parts. It is a short book with the real cover. I lend it for the web workshop. Pickup is the student hub desk. Search for Crockford."),
    ("9780321573513", "lender", "DEMO-DS201", 1, "Robert Sedgewick's Algorithms. I used the sorting chapters beside the Cormen book. This copy is available. The Introduction to Algorithms card is already on loan, so leave that one alone."),
    ("9780262510875", "lender", "DEMO-DS201", 0, "Structure and Interpretation of Computer Programs, by Harold Abelson and Gerald Jay Sussman. I used the first chapter on procedures. Collect it at the library steps. Search for Abelson or Sussman."),
    ("9781617292231", "borrower", "DEMO-DS201", 2, "Jean's copy of Grokking Algorithms by Aditya Bhargava. The pictures helped me before the data structures quiz. I am the owner, so I cannot reserve this card. Another student can take it."),
    ("9781718502703", "lender", "DEMO-CS101", 0, "Eric Matthes, Python Crash Course, third edition. I worked the first projects on my own laptop, so this copy is clean. Library steps. Search for Matthes or Crash Course."),
    ("9780201616224", "borrower", "DEMO-CS101", 1, "Jean's copy of The Pragmatic Programmer by Andrew Hunt and Dave Thomas. I like the broken-windows advice. It is on the lab block bench. This is my copy, so the reserve button is not for me."),
    ("9780131103627", "lender", "DEMO-CS101", 0, "The C Programming Language by Brian Kernighan and Dennis Ritchie. Thin book, real cover. I used the chapter on pointers before the programming practical. Library steps, north side."),
    ("9781492057611", "lender", "DEMO-DS201", 1, "Alan Beaulieu's Learning SQL. I used the join chapter when I wrote the shelf query. It is on the lab block bench. Search for Beaulieu or SQL and this card is the one that matches."),
    ("9781492032649", "lender", "DEMO-DS201", 2, "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow, by Aurelien Geron. Real cover, no writing inside. Student hub desk. Search for Geron or machine learning."),
    ("9780735619678", "lender", "DEMO-CS101", 2, "Steve McConnell's Code Complete. I used the chapters on naming and reviews, and this is a different book from Clean Code. Student hub desk. Search for McConnell or Code Complete."),
)

SEED_ISBNS = CORE_ISBNS + tuple(item[0] for item in EXTRA_COPIES)


def main():
    load_environment()
    if os.environ.get("APP_ENV") == "production":
        raise SystemExit("Refusing to seed when APP_ENV=production.")
    password = os.environ.get("DEMO_STUDENT_PASSWORD", "")
    if len(password) < 12 or password.startswith("replace-with"):
        raise SystemExit("Set DEMO_STUDENT_PASSWORD in .env to at least 12 characters, then run the seed again.")

    records = []
    for isbn in SEED_ISBNS:
        fields = load_fields(isbn)
        if fields:
            records.append(fields)
    if not records:
        raise SystemExit("No edition records were available. Check docs/samples or Open Library, then run the seed again.")

    return_by = campus_today() + timedelta(days=14)
    with transaction() as conn:
        _reset_demo_rows(conn)
        lender_id = _insert_student(
            conn, LENDER_EMAIL, "Amina Niyonsenga", "demonstration lender", password
        )
        borrower_id = _insert_student(
            conn, BORROWER_EMAIL, "Jean Habimana", "demonstration borrower", password
        )
        by_isbn = {}
        for fields in records:
            by_isbn[fields["isbn13"]] = _upsert_edition(conn, fields)
        primary = by_isbn.get(CORE_ISBNS[0]) or next(iter(by_isbn.values()))
        secondary = by_isbn.get(CORE_ISBNS[1], primary)

        demo_copy = _insert_copy(conn, primary, lender_id, "DEMO-CS101", DEMO_LANDMARKS[0], "Bring it back before the Tuesday tutorial. This is the Clean Code copy I offer for the demo.")
        history_copy = _insert_copy(conn, primary, lender_id, "DEMO-WD301", DEMO_LANDMARKS[1], "I already lent this Clean Code copy once. The history row shows that it came back.")
        open_copy = _insert_copy(conn, secondary, lender_id, "DEMO-DS201", DEMO_LANDMARKS[2], "Introduction to Algorithms is already on loan. Leave this card alone during the demo.")
        _insert_copy(conn, primary, borrower_id, "DEMO-CS101", DEMO_LANDMARKS[0], "Jean's spare copy of the same Clean Code edition. I cannot reserve my own card.")
        for isbn, owner, course, landmark_index, note in EXTRA_COPIES:
            edition_id = by_isbn.get(isbn)
            if edition_id is None:
                print(f"skip copy {isbn}")
                continue
            student_id = lender_id if owner == "lender" else borrower_id
            _insert_copy(conn, edition_id, student_id, course, DEMO_LANDMARKS[landmark_index], note)

        finished = reserve_copy(borrower_id, history_copy, return_by, conn=conn)
        if not finished.ok:
            raise SystemExit(finished.message)
        picked = confirm_pickup(lender_id, finished.loan_id, conn=conn)
        if not picked.ok:
            raise SystemExit(picked.message)
        returned = confirm_return(lender_id, finished.loan_id, conn=conn)
        if not returned.ok:
            raise SystemExit(returned.message)

        current = reserve_copy(borrower_id, open_copy, return_by, conn=conn)
        if not current.ok:
            raise SystemExit(current.message)
        current_pickup = confirm_pickup(lender_id, current.loan_id, conn=conn)
        if not current_pickup.ok:
            raise SystemExit(current_pickup.message)

    print(f"seeded {len(records)} edition(s)")
    print(f"lender {LENDER_EMAIL}")
    print(f"borrower {BORROWER_EMAIL}")
    print(f"available copy id {demo_copy}")
    print("history loan returned and open loan picked up")


def load_fields(isbn):
    if os.environ.get("SEED_OFFLINE") != "1":
        result = lookup_isbn(isbn)
        if result.ok:
            print(f"lookup {isbn} {'cache' if result.from_cache else 'openlibrary'}")
            return result.fields
        print(f"lookup {isbn} failed ({result.status}); trying the saved sample")
    sample = ROOT / "docs" / "samples" / f"{isbn}.json"
    if not sample.exists():
        print(f"no sample for {isbn}")
        return None
    payload = json.loads(sample.read_text())
    record = payload.get(f"ISBN:{isbn}")
    if not isinstance(record, dict):
        return None
    fields = map_record(isbn, record)
    if not fields.get("title"):
        return None
    print(f"sample {isbn} {fields['title']}")
    return fields


def _reset_demo_rows(conn):
    conn.execute(
        """
        DELETE FROM loans
        WHERE borrower_id IN (SELECT id FROM students WHERE email LIKE '%@courseshelf.example')
           OR lender_id IN (SELECT id FROM students WHERE email LIKE '%@courseshelf.example')
        """
    )
    conn.execute(
        """
        DELETE FROM copies
        WHERE owner_id IN (SELECT id FROM students WHERE email LIKE '%@courseshelf.example')
        """
    )
    conn.execute("DELETE FROM students WHERE email LIKE '%@courseshelf.example'")


def _insert_student(conn, email, name, label, password):
    row = conn.execute(
        """
        INSERT INTO students (email, display_name, password_hash, demo_label)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (email, name, hash_password(password), label),
    ).fetchone()
    return row["id"]


def _upsert_edition(conn, fields):
    row = conn.execute(
        """
        INSERT INTO editions (
            isbn13, isbn10, title, authors, edition_label, publish_date,
            publishers, cover_url, openlibrary_key, lookup_source
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'openlibrary')
        ON CONFLICT (isbn13) DO UPDATE SET
            isbn10 = EXCLUDED.isbn10,
            title = EXCLUDED.title,
            authors = EXCLUDED.authors,
            edition_label = EXCLUDED.edition_label,
            publish_date = EXCLUDED.publish_date,
            publishers = EXCLUDED.publishers,
            cover_url = EXCLUDED.cover_url,
            openlibrary_key = EXCLUDED.openlibrary_key,
            lookup_source = 'openlibrary'
        RETURNING id
        """,
        (
            fields["isbn13"],
            fields.get("isbn10") or "",
            fields["title"],
            fields.get("authors") or "",
            fields.get("edition_label") or "",
            fields.get("publish_date") or "",
            fields.get("publishers") or "",
            fields.get("cover_url"),
            fields.get("openlibrary_key") or "",
        ),
    ).fetchone()
    return row["id"]


def _insert_copy(conn, edition_id, owner_id, course_code, landmark, note):
    note = note or ""
    if len(note) > 280:
        raise SystemExit("A seed note is longer than 280 characters.")
    course = dict(DEMO_COURSES)[course_code]
    row = conn.execute(
        """
        INSERT INTO copies (edition_id, owner_id, course_code, course_name, pickup_landmark, note, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'available')
        RETURNING id
        """,
        (edition_id, owner_id, course_code, course, landmark, note),
    ).fetchone()
    return row["id"]


if __name__ == "__main__":
    main()
