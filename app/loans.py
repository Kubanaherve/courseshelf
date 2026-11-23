"""I reserve, pick up, return, and cancel from here.

I lock the copy row, then I update it only while it is still available.
If two people reserve together, only one of my updates matches, so I insert one loan.
When I return a copy I make it available again and I leave the loan row in place.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from psycopg.errors import UniqueViolation

from app.core import STATUS_LABELS, campus_today, connection, normalize_isbn, transaction


@dataclass
class ActionResult:
    ok: bool
    message: str
    loan_id: int | None = None


def reserve_copy(student_id, copy_id, return_by, conn=None):
    if not isinstance(return_by, date):
        return ActionResult(False, "Use a real calendar date.")
    today = campus_today()
    if return_by <= today:
        return ActionResult(False, "Return-by must be after today so the lender knows when to expect it back.")
    if return_by > today + timedelta(days=120):
        return ActionResult(False, "Return-by must be within 120 days.")
    return _run(_reserve, student_id, copy_id, return_by, conn=conn)


def confirm_pickup(student_id, loan_id, conn=None):
    return _run(_confirm_pickup, student_id, loan_id, conn=conn)


def confirm_return(student_id, loan_id, conn=None):
    return _run(_confirm_return, student_id, loan_id, conn=conn)


def cancel_reservation(student_id, loan_id, conn=None):
    return _run(_cancel, student_id, loan_id, conn=conn)


def _run(action, *args, conn=None):
    if conn is not None:
        return action(conn, *args)
    try:
        with transaction() as owned:
            return action(owned, *args)
    except UniqueViolation:
        return ActionResult(False, "That copy is no longer available.")


def _reserve(conn, student_id, copy_id, return_by):
    row = conn.execute(
        """
        SELECT id, owner_id, status
        FROM copies
        WHERE id = %s
        FOR UPDATE
        """,
        (copy_id,),
    ).fetchone()
    if row is None:
        return ActionResult(False, "That copy is not on the shelf.")
    if row["owner_id"] == student_id:
        return ActionResult(False, "You offered this copy, so you cannot reserve it.")
    if row["status"] != "available":
        return ActionResult(False, "That copy is no longer available.")

    updated = conn.execute(
        """
        UPDATE copies
        SET status = 'reserved'
        WHERE id = %s AND status = 'available'
        RETURNING id, owner_id
        """,
        (copy_id,),
    ).fetchone()
    if updated is None:
        return ActionResult(False, "That copy is no longer available.")

    loan = conn.execute(
        """
        INSERT INTO loans (copy_id, borrower_id, lender_id, status, return_by)
        VALUES (%s, %s, %s, 'reserved', %s)
        RETURNING id
        """,
        (copy_id, student_id, updated["owner_id"], return_by),
    ).fetchone()
    return ActionResult(
        True,
        "Reserved. Collect it from the pickup landmark, then ask the lender to confirm pickup.",
        loan_id=loan["id"],
    )


def _confirm_pickup(conn, student_id, loan_id):
    loan = _lock_loan(conn, loan_id)
    if loan is None:
        return ActionResult(False, "That loan is not on record.")
    if loan["lender_id"] != student_id:
        return ActionResult(False, "Only the person who offered this copy can confirm pickup.")
    if loan["status"] != "reserved":
        return ActionResult(False, "Pickup can be confirmed only while the copy is reserved.")

    conn.execute(
        """
        UPDATE loans
        SET status = 'picked_up', picked_up_at = now()
        WHERE id = %s
        """,
        (loan_id,),
    )
    moved = conn.execute(
        """
        UPDATE copies
        SET status = 'on_loan'
        WHERE id = %s AND status = 'reserved'
        RETURNING id
        """,
        (loan["copy_id"],),
    ).fetchone()
    if moved is None:
        raise RuntimeError("The copy was not reserved, so pickup was rolled back.")
    return ActionResult(
        True,
        "Pickup confirmed. The copy stays on loan until you confirm the return.",
        loan_id=loan_id,
    )


def _confirm_return(conn, student_id, loan_id):
    loan = _lock_loan(conn, loan_id)
    if loan is None:
        return ActionResult(False, "That loan is not on record.")
    if loan["lender_id"] != student_id:
        return ActionResult(False, "Only the person who offered this copy can confirm the return.")
    if loan["status"] != "picked_up":
        return ActionResult(False, "Confirm the return only after pickup, when the book is back.")

    conn.execute(
        """
        UPDATE loans
        SET status = 'returned', returned_at = now()
        WHERE id = %s
        """,
        (loan_id,),
    )
    moved = conn.execute(
        """
        UPDATE copies
        SET status = 'available'
        WHERE id = %s AND status = 'on_loan'
        RETURNING id
        """,
        (loan["copy_id"],),
    ).fetchone()
    if moved is None:
        raise RuntimeError("The copy was not on loan, so the return was rolled back.")
    return ActionResult(
        True,
        "Return confirmed. The copy is available again, and this loan stays in the history.",
        loan_id=loan_id,
    )


def _cancel(conn, student_id, loan_id):
    loan = _lock_loan(conn, loan_id)
    if loan is None:
        return ActionResult(False, "That loan is not on record.")
    if student_id not in (loan["borrower_id"], loan["lender_id"]):
        return ActionResult(False, "Only the borrower or the lender can cancel this reservation.")
    if loan["status"] != "reserved":
        return ActionResult(False, "A reservation can be cancelled only before pickup.")

    conn.execute(
        """
        UPDATE loans
        SET status = 'cancelled', cancelled_at = now()
        WHERE id = %s
        """,
        (loan_id,),
    )
    moved = conn.execute(
        """
        UPDATE copies
        SET status = 'available'
        WHERE id = %s AND status = 'reserved'
        RETURNING id
        """,
        (loan["copy_id"],),
    ).fetchone()
    if moved is None:
        raise RuntimeError("The copy was not reserved, so the cancellation was rolled back.")
    return ActionResult(True, "Reservation cancelled. The copy is available again.", loan_id=loan_id)


def _lock_loan(conn, loan_id):
    return conn.execute(
        """
        SELECT id, copy_id, borrower_id, lender_id, status
        FROM loans
        WHERE id = %s
        FOR UPDATE
        """,
        (loan_id,),
    ).fetchone()


def loans_for_student(student_id):
    with transaction() as conn:
        borrowing = conn.execute(
            """
            SELECT l.id, l.status, l.return_by, l.reserved_at, l.picked_up_at,
                   e.title, e.authors, e.isbn13, e.edition_label,
                   c.course_code, c.pickup_landmark, s.display_name AS other_name
            FROM loans AS l
            JOIN copies AS c ON c.id = l.copy_id
            JOIN editions AS e ON e.id = c.edition_id
            JOIN students AS s ON s.id = l.lender_id
            WHERE l.borrower_id = %s AND l.status IN ('reserved', 'picked_up')
            ORDER BY l.return_by ASC, l.id ASC
            """,
            (student_id,),
        ).fetchall()
        lending = conn.execute(
            """
            SELECT l.id, l.status, l.return_by, l.reserved_at, l.picked_up_at,
                   e.title, e.authors, e.isbn13, e.edition_label,
                   c.course_code, c.pickup_landmark, s.display_name AS other_name
            FROM loans AS l
            JOIN copies AS c ON c.id = l.copy_id
            JOIN editions AS e ON e.id = c.edition_id
            JOIN students AS s ON s.id = l.borrower_id
            WHERE l.lender_id = %s AND l.status IN ('reserved', 'picked_up')
            ORDER BY l.return_by ASC, l.id ASC
            """,
            (student_id,),
        ).fetchall()
        history = conn.execute(
            """
            SELECT l.id, l.status, l.return_by, l.returned_at, l.cancelled_at,
                   e.title, e.isbn13, c.course_code,
                   borrower.display_name AS borrower_name,
                   lender.display_name AS lender_name
            FROM loans AS l
            JOIN copies AS c ON c.id = l.copy_id
            JOIN editions AS e ON e.id = c.edition_id
            JOIN students AS borrower ON borrower.id = l.borrower_id
            JOIN students AS lender ON lender.id = l.lender_id
            WHERE l.status IN ('returned', 'cancelled')
              AND (l.borrower_id = %s OR l.lender_id = %s)
            ORDER BY l.id DESC
            """,
            (student_id, student_id),
        ).fetchall()
    return {
        "borrowing": [dict(row) for row in borrowing],
        "lending": [dict(row) for row in lending],
        "history": [dict(row) for row in history],
    }

"""I search my shelf here. I match the title and ISBN as data, and I never paste the search text into my SQL."""


def search_copies(course, availability, query, sort):
    like = None
    isbn = None
    text = (query or "").strip()
    if text:
        isbn = normalize_isbn(text)
        escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"

    if availability not in ("", "available", "reserved", "on_loan"):
        availability = ""
    if sort not in ("title", "return_by"):
        sort = "title"

    with connection() as conn:
        rows = conn.execute(
            """
            SELECT
                c.id,
                c.status,
                c.course_code,
                c.course_name,
                c.pickup_landmark,
                c.note,
                c.owner_id,
                s.display_name AS owner_name,
                e.title,
                e.authors,
                e.edition_label,
                e.isbn13,
                e.cover_url,
                e.publish_date,
                l.return_by,
                l.status AS loan_status
            FROM copies AS c
            JOIN editions AS e ON e.id = c.edition_id
            JOIN students AS s ON s.id = c.owner_id
            LEFT JOIN loans AS l
                ON l.copy_id = c.id
               AND l.status IN ('reserved', 'picked_up')
            WHERE (%(course)s = '' OR c.course_code = %(course)s)
              AND (%(availability)s = '' OR c.status = %(availability)s)
              AND (
                    %(like)s::text IS NULL
                    OR e.title ILIKE %(like)s ESCAPE '\\'
                    OR e.authors ILIKE %(like)s ESCAPE '\\'
                    OR c.note ILIKE %(like)s ESCAPE '\\'
                    OR (%(isbn)s::text IS NOT NULL AND e.isbn13 = %(isbn)s)
                  )
            ORDER BY
                CASE WHEN %(sort)s = 'return_by' THEN l.return_by END ASC NULLS LAST,
                e.title ASC,
                c.id ASC
            """,
            {
                "course": course or "",
                "availability": availability,
                "like": like,
                "isbn": isbn,
                "sort": sort,
            },
        ).fetchall()
    copies = []
    for row in rows:
        item = dict(row)
        item["status_label"] = STATUS_LABELS.get(item["status"], item["status"])
        copies.append(item)
    return copies

"""I add a physical copy of an edition I can lend."""

from app.openlibrary import read_cache


def publish_copy(owner_id, isbn13, title, authors, edition_label, course_code, course_name, landmark, note):
    title = (title or "").strip()
    authors = (authors or "").strip()
    edition_label = (edition_label or "").strip()
    note = (note or "").strip()

    with transaction() as conn:
        existing = conn.execute(
            "SELECT id, title FROM editions WHERE isbn13 = %s",
            (isbn13,),
        ).fetchone()
        if existing:
            edition_id = existing["id"]
            stored_title = existing["title"]
            source = "existing"
        else:
            cached = read_cache(isbn13)
            if cached and cached.get("title"):
                stored_title = cached["title"]
                stored_authors = cached["authors"]
                stored_edition = cached["edition_label"] or edition_label
                conn.execute(
                    """
                    INSERT INTO editions (
                        isbn13, isbn10, title, authors, edition_label, publish_date,
                        publishers, cover_url, openlibrary_key, lookup_source
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'openlibrary')
                    """,
                    (
                        isbn13,
                        cached["isbn10"],
                        stored_title,
                        stored_authors,
                        stored_edition,
                        cached["publish_date"],
                        cached["publishers"],
                        cached["cover_url"],
                        cached["openlibrary_key"],
                    ),
                )
                source = "openlibrary"
            else:
                if not title or not authors:
                    return None, "Enter the title and the author. Open Library did not supply them."
                stored_title = title
                conn.execute(
                    """
                    INSERT INTO editions (
                        isbn13, title, authors, edition_label, lookup_source
                    )
                    VALUES (%s, %s, %s, %s, 'manual')
                    """,
                    (isbn13, title, authors, edition_label),
                )
                source = "manual"
            edition_id = conn.execute(
                "SELECT id FROM editions WHERE isbn13 = %s",
                (isbn13,),
            ).fetchone()["id"]

        copy = conn.execute(
            """
            INSERT INTO copies (
                edition_id, owner_id, course_code, course_name, pickup_landmark, note, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'available')
            RETURNING id
            """,
            (edition_id, owner_id, course_code, course_name, landmark, note),
        ).fetchone()

    if source == "existing":
        message = f"Your copy was added to the edition already recorded for this ISBN: {stored_title}."
    elif source == "openlibrary":
        message = f"Your copy of {stored_title} is on the shelf. The title and author came from Open Library."
    else:
        message = f"Your copy of {stored_title} is on the shelf. You entered the details because Open Library had no usable record."
    return copy["id"], message
