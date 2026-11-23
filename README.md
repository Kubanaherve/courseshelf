# CourseShelf

Developed by Herve Friend KUBANA

I built CourseShelf for my ALU Kigali tutorial. It answers one question: can I borrow this exact edition before the tutorial, and where do I collect it?

This is my demonstration. It is not an official ALU service, and it does not use university sign-on. The people, courses, and pickup points in my seed data are fictional and labeled as demonstrations.

## Links for this assignment

- My public GitHub repository: PUBLIC_GITHUB_URL
- My demo video, 2 minutes or less: VIDEO_URL
- My local shelf: http://127.0.0.1:5050/
- My deployed website: https://www.friendherve.tech
- Open Library Books API documentation: https://openlibrary.org/dev/docs/api/books

## What I can do on the shelf

I keep three screens.

- **Shelf** at `/` searches by title, author, note, or ISBN, filters by course and availability, and sorts by title or return-by date.
- **Offer** at `/offer` looks up an ISBN and publishes one physical copy.
- **Loans** at `/loans` shows what I am borrowing and what other people are borrowing from me.

A guest can browse. Reserving, offering, pickup, return, and cancel all require a login. I sign the session cookie with `SECRET_KEY`. I protect every POST form with a token that must match the session.

## The accounts I created

I created two accounts with the seed. I use the same password for both. I also paste these details into the assignment comment box.

| Role | Name | Email |
| --- | --- | --- |
| Lender | Amina Niyonsenga | amina.demo@courseshelf.example |
| Borrower | Jean Habimana | jean.demo@courseshelf.example |

Password: DEMO_PASSWORD_HERE

There is no public registration page. I do not store this password on the login page.

## The records I seed

I seed three demonstration courses and three pickup points.

- `DEMO-CS101` Demonstration: Introduction to Programming. Pickup: Demo pickup: library steps (north).
- `DEMO-DS201` Demonstration: Data Structures. Pickup: Demo pickup: lab block bench.
- `DEMO-WD301` Demonstration: Web Infrastructure Workshop. Pickup: Demo pickup: student hub desk.

I store real editions from Open Library, and I keep the real cover image when Open Library gives me one. Two of them carry the loan story.

- ISBN `9780132350884`, Clean Code, Robert C. Martin. The record has no edition name, so I show “Edition not stated”.
- ISBN `9780262033848`, Introduction to Algorithms, Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein. I leave this copy on loan.

I also offer Effective Java, Design Patterns, Designing Data-Intensive Applications, Clean Architecture, Head First Design Patterns, Refactoring, JavaScript: The Good Parts, Algorithms by Sedgewick, Structure and Interpretation of Computer Programs, Grokking Algorithms, Python Crash Course, The Pragmatic Programmer, The C Programming Language, Learning SQL, Hands-On Machine Learning, and Code Complete. Each card has a longer note in the lender’s own words. I can search a title, an author such as Kleppmann, or a word from a note such as replication.

The seed also walks one Clean Code copy through reserve, pickup, and return, and leaves the algorithms copy on loan so the shelf has a return-by date. I can run the seed again. It does not duplicate the open loan.

## The stack I pinned

I pinned these on 22 Nov 2026 from my own `pip freeze`, Python 3.14.6, macOS arm64.

| Package | Version |
| --- | --- |
| Flask | 3.1.3 |
| Jinja2 | 3.1.6 |
| Werkzeug | 3.1.9 |
| Gunicorn | 27.0.1 |
| psycopg | 3.3.9 |
| python-dotenv | 1.2.4 |

I use PostgreSQL 16 on my Mac. I do not use a database password. `DATABASE_URL=postgresql:///courseshelf` connects through the local socket. I use plain CSS and the browser’s system font, so the pages work when I am offline. I load a cover only from `https://covers.openlibrary.org/` when Open Library gives me one.

## What my Mac needs before the first run

- Python 3.12 or newer. I developed this with Python 3.14.6.
- PostgreSQL 16. On my Mac the tools are in `/opt/homebrew/opt/postgresql@16/bin`.
- A browser.
- The intranet lab containers `web-01`, `web-02`, and `lb-01` when I want the two servers and the load balancer. I did not create new servers.

## How I set it up the first time

I run these commands from the repository root.

```bash
bash scripts/setup.sh
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
createdb courseshelf || true
.venv/bin/python scripts/migrate.py
.venv/bin/python scripts/seed.py
```

`scripts/setup.sh` creates `.venv`, installs `requirements.txt`, and copies `.env.example` to `.env` only when `.env` is missing. I then set two values in `.env` and I never commit that file.

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

I put that 64-character hex value in `SECRET_KEY`. I put a password of at least 12 characters in `DEMO_STUDENT_PASSWORD`. I leave `FLASK_DEBUG=0`. I leave `APP_ENV=local` on my Mac.

## The settings I keep in .env

| Name | What I set | Who reads it |
| --- | --- | --- |
| `APP_ENV` | `local` on my Mac | The app refuses to boot in production when debug is on or the secret is a placeholder |
| `FLASK_DEBUG` | `0` | Flask |
| `SECRET_KEY` | 64 hex characters | Signed session cookies. Web01 and Web02 must share this value |
| `DATABASE_URL` | `postgresql:///courseshelf` | psycopg |
| `BACKEND_NAME` | `local`, or `web01` and `web02` on the servers | The footer and the `X-CourseShelf-Backend` header |
| `PORT` | `5050` | The local shelf. macOS often holds port 5000 |
| `OPENLIBRARY_TIMEOUT_SECONDS` | `6` | My Open Library client |
| `OPENLIBRARY_USER_AGENT` | `CourseShelf/1.0 (Herve Friend KUBANA; +https://openlibrary.org/dev/docs/api/books)` | The request I send to Open Library |
| `DEMO_STUDENT_PASSWORD` | the password in the table above | The seed, when it hashes the two accounts |

## How I run the local shelf

```bash
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
.venv/bin/flask --app wsgi run --host 127.0.0.1 --port 5050
```

I leave that Terminal window open. I open http://127.0.0.1:5050/. If the port is already in use, the shelf is already running.

## The Open Library API

I do not use an API key. The Open Library Books API does not require one, and I do not store a key in this project.

I call one documented endpoint:

`GET https://openlibrary.org/api/books?bibkeys=ISBN:{isbn13}&format=json&jscmd=data`

Official documentation: https://openlibrary.org/dev/docs/api/books

I strip spaces and hyphens, I check the ISBN-10 or ISBN-13 check digit, and I store the ISBN-13. I send only that ISBN. I never guess an edition from the title. I cache a successful response in `isbn_lookups`. I do not cache a timeout, a rate limit, or a missing record, so a later lookup can succeed. When the author is missing I show “Author not listed”. When the edition is missing I show “Edition not stated”.

I mapped those fields from a real Books API response.

## The loan rules I enforce

I follow the Africa/Kigali calendar. I show dates as `22 Nov 2026`. The default return-by date is 14 days after today. I accept a return-by date only when it is after today and within 120 days.

I will not let the owner reserve their own copy. A reservation locks the copy and changes it from available to reserved only while it is still available, so two people cannot take the same copy. The lender confirms pickup, which moves the copy to on loan. The lender confirms the return, which makes the copy available again and keeps the loan row. The borrower or the lender can cancel a reservation that has not been picked up.

## How I test it

I test with the browser and with `curl`. I do these checks in this order after the seed.

1. I open http://127.0.0.1:5050/healthz and I expect HTTP 200 and `"database": "ok"`.
2. I open http://127.0.0.1:5050/ and I expect the heading Course shelf, the name Herve Friend KUBANA, and the book Clean Code.
3. I search for `9780132350884`. I expect only Clean Code. I search for `Kleppmann` and I expect Designing Data-Intensive Applications. I clear the search and I expect the other books to return.
4. I open Offer while I am signed out. I expect the login page.
5. I sign in as `jean.demo@courseshelf.example` with the password above. I look up ISBN `9780132350884`. I expect the title Clean Code and the author Robert C. Martin, and I expect the edition box to stay blank.
6. I try ISBN `0`. I expect an error that tells me the ISBN is not valid, and I expect the form to keep what I typed.
7. As Jean, I reserve an available copy that Amina offered. I expect it on My loans as reserved. I expect the same copy to disappear from “available” for a second visitor.
8. I try to reserve my own copy. I expect a refusal.
9. I sign out and I sign in as `amina.demo@courseshelf.example`. I confirm pickup, then I confirm the return. I expect the copy to become available again and the loan to stay in the history.
10. I reserve another copy as Jean and I cancel it before pickup. I expect the copy to become available again.

The health command I use:

```bash
curl -sS http://127.0.0.1:5050/healthz
```

I expect a body like this:

```json
{"backend":"local","database":"ok","status":"ok"}
```

## How I check the intranet servers

I use the Web Infrastructure lab containers. web-01 answers on http://127.0.0.1:8080/ and the response header `X-CourseShelf-Backend` is `web01`. web-02 answers on http://127.0.0.1:8081/ and that header is `web02`. Neither direct server sends `X-Served-By`. The load balancer, lb-01, answers on http://127.0.0.1:8082/. HAProxy adds `X-Served-By` after it chooses a server, so that header exists only on the load balancer. Refreshing it changes `X-Served-By` between `web-01` and `web-02`, and `X-CourseShelf-Backend` between `web01` and `web02`. The footer shows the same name. The header is the signal I trust, because the page cannot invent a header that only HAProxy adds.

```bash
curl -sSI http://127.0.0.1:8080/healthz
curl -sSI http://127.0.0.1:8081/healthz
curl -sSI http://127.0.0.1:8082/healthz
```

Both web servers read the same database, so a reservation I make on web-01 is visible on web-02. I use the same `SECRET_KEY` and the same `DATABASE_URL` for both. My database stays on my Mac because the course containers do not include PostgreSQL. The lab certificate is `/etc/ssl/certs/ha_proxy_ssl.pem`. I did not issue a Let's Encrypt certificate, because `127.0.0.1` is not a public name. I did not create new servers.

## The website I submit

The website a reviewer can open is https://www.friendherve.tech. `www` already points at my load balancer. HAProxy accepts HTTPS with the certificate for that name and sends each request to web-01 or web-02. When I refresh the page, the footer changes between `web01` and `web02`. I did not change the DNS records. A request to a raw server address still returns Holberton School. The name was already serving an earlier copy of this app. After my own folder works on my Mac, I publish that folder to web-01 and web-02, so the same address shows the files I created.

## The files in this repository

```text
wsgi.py                     I start the app from here
app/                        the app, the Open Library client, loans, and the pages
app/templates/              shelf, offer, loans, login, and the error page
migrations/001_schema.sql   my tables
scripts/setup.sh            virtualenv and install
scripts/migrate.py          apply the SQL
scripts/seed.py             demonstration accounts and copies
```

## Problems I solved

Open Library’s documentation page timed out, so I mapped the fields from a real Books API response. I use port 5050 because macOS often holds port 5000. The course containers do not include PostgreSQL, so the database runs on my Mac. Let's Encrypt cannot see `127.0.0.1`, so I keep the lab certificate.

## Credit

Developed by Herve Friend KUBANA.

Book records and covers come from the Internet Archive Open Library. I used Flask, Jinja, Werkzeug, Gunicorn, psycopg, and PostgreSQL.
