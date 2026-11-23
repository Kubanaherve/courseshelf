"""I talk to my PostgreSQL database from here. I commit each loan change in its own transaction."""

import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


def database_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and set it.")
    return url


def connect():
    return psycopg.connect(database_url(), row_factory=dict_row)


@contextmanager
def connection():
    with connect() as conn:
        yield conn


@contextmanager
def transaction():
    with connect() as conn:
        with conn.transaction():
            yield conn


"""I normalize ISBN-10 and ISBN-13 values.

I calculate the check digit myself. I never turn a title into an ISBN or an edition.
"""


def normalize_isbn(raw):
    """I return a valid ISBN-13, or nothing when my input is missing or invalid."""
    if raw is None:
        return None
    text = "".join(ch for ch in str(raw).strip().upper() if ch.isalnum())
    if len(text) == 10 and _isbn10_valid(text):
        return _isbn10_to_isbn13(text)
    if len(text) == 13 and text.isdigit() and _isbn13_valid(text):
        return text
    return None


def _isbn10_valid(isbn10):
    if len(isbn10) != 10:
        return False
    if not isbn10[:9].isdigit():
        return False
    if not (isbn10[9].isdigit() or isbn10[9] == "X"):
        return False
    total = 0
    for index, character in enumerate(isbn10):
        value = 10 if character == "X" else int(character)
        total += value * (10 - index)
    return total % 11 == 0


def _isbn13_valid(isbn13):
    if len(isbn13) != 13 or not isbn13.isdigit():
        return False
    if not isbn13.startswith(("978", "979")):
        return False
    return _isbn13_check_digit(isbn13[:12]) == isbn13[12]


def _isbn13_check_digit(first_twelve):
    total = 0
    for index, character in enumerate(first_twelve):
        number = int(character)
        total += number if index % 2 == 0 else number * 3
    return str((10 - (total % 10)) % 10)


def _isbn10_to_isbn13(isbn10):
    body = "978" + isbn10[:9]
    return body + _isbn13_check_digit(body)


"""I set the display rules for my shelf.

I follow the Africa/Kigali calendar. I label my course codes and pickup points
as demonstrations. They are not an official ALU catalog.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CAMPUS_TZ = ZoneInfo("Africa/Kigali")

DEMO_COURSES = (
    ("DEMO-CS101", "Demonstration: Introduction to Programming"),
    ("DEMO-DS201", "Demonstration: Data Structures"),
    ("DEMO-WD301", "Demonstration: Web Infrastructure Workshop"),
)

DEMO_LANDMARKS = (
    "Demo pickup: library steps (north)",
    "Demo pickup: lab block bench",
    "Demo pickup: student hub desk",
)

AVAILABILITY_OPTIONS = (
    ("", "Any availability"),
    ("available", "Available now"),
    ("reserved", "Reserved"),
    ("on_loan", "On loan"),
)

SORT_OPTIONS = (
    ("title", "Title"),
    ("return_by", "Return-by date"),
)

STATUS_LABELS = {
    "available": "Available now",
    "reserved": "Reserved",
    "on_loan": "On loan",
    "picked_up": "On loan",
    "returned": "Returned",
    "cancelled": "Cancelled",
}

LENDER_EMAIL = "amina.demo@courseshelf.example"
BORROWER_EMAIL = "jean.demo@courseshelf.example"


def campus_today():
    return datetime.now(CAMPUS_TZ).date()


def default_return_by():
    return campus_today() + timedelta(days=14)


def format_date(value):
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        value = value.astimezone(CAMPUS_TZ).date()
    if hasattr(value, "strftime") and not isinstance(value, str):
        return value.strftime("%d %b %Y")
    text = str(value).strip()
    if len(text) >= 10:
        parsed = datetime.strptime(text[:10], "%Y-%m-%d").date()
        return parsed.strftime("%d %b %Y")
    return ""


def parse_return_by(raw):
    text = (raw or "").strip()
    if not text:
        return None, "Choose the date you must return the book, before your next tutorial."
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None, "Use a real calendar date."
    today = campus_today()
    if parsed <= today:
        return None, "Return-by must be after today so the lender knows when to expect it back."
    if parsed > today + timedelta(days=120):
        return None, "Return-by must be within 120 days."
    return parsed, None


def course_name(code):
    for known, name in DEMO_COURSES:
        if known == code:
            return name
    return None


def known_landmark(value):
    return value in DEMO_LANDMARKS


"""I handle login, password checks, and form protection.

I store passwords only as Werkzeug hashes. My database check rejects a short hash.
"""

import secrets

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

_DUMMY_HASH = generate_password_hash("courseshelf-dummy-password")


def hash_password(password):
    return generate_password_hash(password)


def authenticate(email, password):
    """I return the account id, or nothing. I still run a hash check when the account is missing."""
    normalized = (email or "").strip().lower()
    with connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM students WHERE email = %s",
            (normalized,),
        ).fetchone()
    if row is None:
        check_password_hash(_DUMMY_HASH, password or "")
        return None
    if not check_password_hash(row["password_hash"], password or ""):
        return None
    return row["id"]


def current_student():
    student_id = session.get("student_id")
    if not student_id:
        return None
    with connection() as conn:
        return conn.execute(
            """
            SELECT id, email, display_name, demo_label
            FROM students
            WHERE id = %s
            """,
            (student_id,),
        ).fetchone()


def ensure_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def rotate_session(student_id):
    """I drop the old session so a login cannot reuse an id I issued before."""
    session.clear()
    session["student_id"] = student_id
    session["csrf_token"] = secrets.token_urlsafe(32)
    session.permanent = False


def csrf_tokens_match(sent, expected):
    if not isinstance(sent, str) or not isinstance(expected, str):
        return False
    if not sent or not expected or len(sent) != len(expected):
        return False
    return secrets.compare_digest(sent, expected)


def safe_next_path(value):
    if not isinstance(value, str):
        return None
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return None
    return value

