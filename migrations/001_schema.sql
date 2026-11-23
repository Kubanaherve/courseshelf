-- I designed this schema. Developed by Herve Friend KUBANA.
-- One of my editions can have many physical copies.
-- I treat an open loan as reserved or picked up. I keep returned and cancelled rows.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS students (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    demo_label TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT students_email_shape CHECK (position('@' IN email) > 1),
    CONSTRAINT students_password_is_hashed CHECK (char_length(password_hash) >= 20)
);

CREATE TABLE IF NOT EXISTS editions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn13 TEXT NOT NULL UNIQUE,
    isbn10 TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    edition_label TEXT NOT NULL DEFAULT '',
    publish_date TEXT NOT NULL DEFAULT '',
    publishers TEXT NOT NULL DEFAULT '',
    cover_url TEXT,
    openlibrary_key TEXT NOT NULL DEFAULT '',
    lookup_source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT editions_isbn13_shape CHECK (isbn13 ~ '^[0-9]{13}$'),
    CONSTRAINT editions_source_known CHECK (lookup_source IN ('openlibrary', 'manual'))
);

CREATE TABLE IF NOT EXISTS isbn_lookups (
    isbn13 TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT NOT NULL DEFAULT '',
    edition_label TEXT NOT NULL DEFAULT '',
    publish_date TEXT NOT NULL DEFAULT '',
    publishers TEXT NOT NULL DEFAULT '',
    cover_url TEXT,
    isbn10 TEXT NOT NULL DEFAULT '',
    openlibrary_key TEXT NOT NULL DEFAULT '',
    payload JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT isbn_lookups_isbn13_shape CHECK (isbn13 ~ '^[0-9]{13}$')
);

CREATE TABLE IF NOT EXISTS copies (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    edition_id BIGINT NOT NULL REFERENCES editions (id),
    owner_id BIGINT NOT NULL REFERENCES students (id),
    course_code TEXT NOT NULL,
    course_name TEXT NOT NULL,
    pickup_landmark TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT copies_status_known CHECK (status IN ('available', 'reserved', 'on_loan'))
);

CREATE TABLE IF NOT EXISTS loans (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    copy_id BIGINT NOT NULL REFERENCES copies (id),
    borrower_id BIGINT NOT NULL REFERENCES students (id),
    lender_id BIGINT NOT NULL REFERENCES students (id),
    status TEXT NOT NULL,
    return_by DATE NOT NULL,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    picked_up_at TIMESTAMPTZ,
    returned_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    CONSTRAINT loans_status_known CHECK (status IN ('reserved', 'picked_up', 'returned', 'cancelled')),
    CONSTRAINT loans_distinct_people CHECK (borrower_id <> lender_id)
);

CREATE INDEX IF NOT EXISTS copies_course_idx ON copies (course_code);
CREATE INDEX IF NOT EXISTS copies_status_idx ON copies (status);
CREATE INDEX IF NOT EXISTS loans_borrower_idx ON loans (borrower_id);
CREATE INDEX IF NOT EXISTS loans_lender_idx ON loans (lender_id);

-- The conditional update in the reservation is the race lock.
-- This index is a second guard so two open loans cannot share one copy.
CREATE UNIQUE INDEX IF NOT EXISTS loans_one_open_per_copy
    ON loans (copy_id)
    WHERE status IN ('reserved', 'picked_up');
