"""I call the Open Library Books API from here. Developed by Herve Friend KUBANA.

I use https://openlibrary.org/dev/docs/api/books
I saved one successful response on 22 Nov 2026 for ISBN 9780132350884.
I keep my field map in docs/openlibrary.md.

I send only a normalized ISBN. I never guess an edition from the title.
I cache a success. I do not cache a failure, so I can try again later.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from app.core import connection


API_URL = "https://openlibrary.org/api/books"
DEFAULT_USER_AGENT = (
    "CourseShelf/1.0 "
    "(Herve Friend KUBANA; +https://openlibrary.org/dev/docs/api/books)"
)
COVER_PREFIX = "https://covers.openlibrary.org/"

TIMEOUT_MESSAGE = (
    "Open Library did not answer in time. Your entries are still in the form. "
    "Wait a moment and look up again, or publish with the fields you typed."
)
RATE_MESSAGE = (
    "Open Library asked us to slow down. Your entries are still in the form. "
    "Wait a minute, then look up again, or publish with the fields you typed."
)
OUTAGE_MESSAGE = (
    "Open Library could not be reached. Your entries are still in the form. "
    "Publish with the fields you typed, or try the lookup again later."
)
UNKNOWN_MESSAGE = (
    "Open Library has no record for this ISBN. The form is unchanged. "
    "Enter the title, author, and edition from the book, then publish."
)
MISSING_MESSAGE = (
    "Open Library returned a record with fields missing. "
    "Fill the empty boxes from the book. The edition box is left blank unless the record states one."
)


@dataclass
class LookupResult:
    status: str
    message: str
    fields: dict = field(default_factory=dict)
    from_cache: bool = False

    @property
    def ok(self):
        return self.status == "ok"


def lookup_isbn(isbn13, opener=None):
    """I look up one ISBN-13. I accept an opener so I can test this without the network."""
    cached = read_cache(isbn13)
    if cached:
        return LookupResult(
            "ok",
            "Loaded the saved Open Library record for this ISBN.",
            cached,
            from_cache=True,
        )

    timeout = _timeout_seconds()
    user_agent = os.environ.get("OPENLIBRARY_USER_AGENT", DEFAULT_USER_AGENT).strip() or DEFAULT_USER_AGENT
    params = urllib.parse.urlencode(
        {"bibkeys": f"ISBN:{isbn13}", "format": "json", "jscmd": "data"}
    )
    request = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )
    try:
        if opener is None:
            response_context = urllib.request.urlopen(request, timeout=timeout)
        else:
            response_context = opener(request, timeout)
        with response_context as response:
            status_code = getattr(response, "status", 200)
            body = response.read(1_000_000)
    except TimeoutError:
        return LookupResult("timeout", TIMEOUT_MESSAGE)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return LookupResult("rate_limit", RATE_MESSAGE)
        return LookupResult("outage", OUTAGE_MESSAGE)
    except (urllib.error.URLError, OSError):
        return LookupResult("outage", OUTAGE_MESSAGE)

    if status_code == 429:
        return LookupResult("rate_limit", RATE_MESSAGE)
    if status_code >= 400:
        return LookupResult("outage", OUTAGE_MESSAGE)

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return LookupResult("outage", OUTAGE_MESSAGE)
    if not isinstance(payload, dict):
        return LookupResult("outage", OUTAGE_MESSAGE)

    record = payload.get(f"ISBN:{isbn13}")
    if not isinstance(record, dict):
        return LookupResult("unknown", UNKNOWN_MESSAGE)

    fields = map_record(isbn13, record)
    if not fields.get("title"):
        return LookupResult("missing_fields", MISSING_MESSAGE, fields)

    write_cache(fields, record)
    return LookupResult("ok", "Open Library returned this edition.", fields)


def map_record(isbn13, record):
    """I copy the fields I show on my shelf. I take the edition only from an edition field, never from the title."""
    authors = []
    for item in record.get("authors") or []:
        if isinstance(item, dict) and item.get("name"):
            authors.append(str(item["name"]).strip())

    publishers = []
    for item in record.get("publishers") or []:
        if isinstance(item, dict) and item.get("name"):
            publishers.append(str(item["name"]).strip())
        elif isinstance(item, str) and item.strip():
            publishers.append(item.strip())

    cover = record.get("cover") if isinstance(record.get("cover"), dict) else {}
    cover_url = safe_cover(cover.get("medium") or cover.get("large") or cover.get("small"))

    identifiers = record.get("identifiers") if isinstance(record.get("identifiers"), dict) else {}
    isbn10_values = identifiers.get("isbn_10") or []
    isbn10 = str(isbn10_values[0]).strip() if isbn10_values else ""

    edition_label = ""
    for key in ("edition_name", "edition"):
        raw_edition = record.get(key)
        if isinstance(raw_edition, str) and raw_edition.strip():
            edition_label = raw_edition.strip()
            break

    title = record.get("title")
    title = title.strip() if isinstance(title, str) else ""
    publish_date = record.get("publish_date")
    publish_date = publish_date.strip() if isinstance(publish_date, str) else ""
    ol_key = record.get("key")
    ol_key = ol_key.strip() if isinstance(ol_key, str) else ""

    return {
        "isbn13": isbn13,
        "isbn10": isbn10,
        "title": title,
        "authors": ", ".join(authors),
        "edition_label": edition_label,
        "publish_date": publish_date,
        "publishers": ", ".join(publishers),
        "cover_url": cover_url,
        "openlibrary_key": ol_key,
    }


def safe_cover(url):
    if isinstance(url, str) and url.startswith(COVER_PREFIX):
        return url
    return None


def read_cache(isbn13):
    with connection() as conn:
        row = conn.execute(
            """
            SELECT isbn13, isbn10, title, authors, edition_label, publish_date,
                   publishers, cover_url, openlibrary_key
            FROM isbn_lookups
            WHERE isbn13 = %s
            """,
            (isbn13,),
        ).fetchone()
    return dict(row) if row else None


def write_cache(fields, record):
    with connection() as conn:
        with conn.transaction():
            conn.execute(
                """
                INSERT INTO isbn_lookups (
                    isbn13, title, authors, edition_label, publish_date, publishers,
                    cover_url, isbn10, openlibrary_key, payload
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (isbn13) DO NOTHING
                """,
                (
                    fields["isbn13"],
                    fields["title"],
                    fields["authors"],
                    fields["edition_label"],
                    fields["publish_date"],
                    fields["publishers"],
                    fields["cover_url"],
                    fields["isbn10"],
                    fields["openlibrary_key"],
                    json.dumps(record),
                ),
            )


def _timeout_seconds():
    raw = os.environ.get("OPENLIBRARY_TIMEOUT_SECONDS", "6").strip()
    try:
        value = float(raw)
    except ValueError:
        return 6.0
    if value <= 0 or value > 20:
        return 6.0
    return value
