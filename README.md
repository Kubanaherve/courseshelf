# CourseShelf

Developed by Herve Friend KUBANA

I built CourseShelf for my ALU Kigali tutorial. It answers one question before a class: can I borrow this exact edition, and where on campus do I collect it?

This is my demonstration. It is not an official ALU service, and it does not use university sign-on. The students, courses, and pickup points in the seed are fictional and labeled as demonstrations. The book records and the cover images come from the Open Library Books API.

## Links for this assignment

- My public GitHub repository: https://github.com/Kubanaherve/courseshelf
- My demo video, 2 minutes or less: VIDEO_URL
- My local shelf: http://127.0.0.1:5050/
- web-01 in the lab: http://127.0.0.1:8080/
- web-02 in the lab: http://127.0.0.1:8081/
- My load balancer, shown in the video: http://127.0.0.1:8082/
- My deployed website: https://www.friendherve.tech
- Open Library Books API documentation: https://openlibrary.org/dev/docs/api/books

There is no API key. The Open Library Books API does not require one, and this repository does not contain one.

I paste the same fact into the assignment comment box, together with the two emails and the password below. A reviewer who opens the public repository, the video, and https://www.friendherve.tech can use the application without asking me for another password.

## The problem

A tutorial assigns a reading by page. A book with a similar title can be a different edition, and then the exercises do not match the class. Buying or importing that exact paper copy in Kigali is slow and expensive. Students already lend books to each other, but a chat message does not record who has the copy, when it must come back, or where the two people will meet.

I needed a shelf with four properties.

- The edition is the one Open Library returns for that ISBN, not a guess from the title.
- Each physical copy belongs to one course and one campus pickup point.
- A student can search, filter, and sort before asking to borrow.
- Two students cannot take the same copy, and the owner confirms the real handover and the real return.

CourseShelf is that shelf.

## What a reviewer can do

I keep three screens. A guest can browse. Anything that changes a copy requires a login.

### Shelf, at `/`

The shelf is the catalog of physical copies.

The search box accepts a title, an author, a note, or an ISBN. I click **Apply**. The search is not a live search. `Kleppmann` returns Designing Data-Intensive Applications. `replication` matches the note on that card. `9780132350884` and `978-0-13-235088-4` both return Clean Code, because I normalize the ISBN before I compare it.

The course menu limits the shelf to one demonstration course. The availability menu limits it to available, reserved, or on loan. The sort menu orders the cards by title, or by return-by date with the soonest date first.

Each card shows the cover when Open Library provided one, the title, the authors, the ISBN-13, the edition, the course, the pickup point, the availability, the return-by date, the student who offered the copy, and that student’s note. An available copy has a return-by date and a **Reserve this copy** button. The date defaults to 14 days after today in Africa/Kigali. I accept a date only when it is after today and within 120 days. The owner of a copy sees that another student can reserve it. A guest sees a link to log in.

### Offer, at `/offer`

A signed-in student publishes one physical copy.

The form asks for an ISBN, a title, an author, an edition, a course, a pickup landmark, and a note of at most 280 characters. **Look up this ISBN** calls Open Library and fills the title, the author, and the edition from that record. The edition box stays empty when the record has no edition name. **Publish this copy** stores one copy. The return-by date is not on this form. The borrower chooses it later, on the shelf, at the moment of the reservation.

A bad ISBN stays in the form. A failed lookup also leaves the typed values in place, so the student can correct the ISBN or publish the fields by hand.

### Loans, at `/loans`

This screen has two sides.

**Books I want to borrow** lists the reservations and the loans of the signed-in student, including where to collect the copy and the return-by date. A reservation that has not been picked up can be cancelled by the borrower or the lender.

**Copies other students asked to borrow** lists the copies I offered. For a reservation I click **Confirm pickup**. The copy becomes on loan. I then click **Confirm return**. The copy becomes available again, and the loan stays in the history. I do not delete the history row.

## The accounts

The seed creates both accounts. They share one password. I do not print the password on the login page. I store a Werkzeug hash.

| Role on the shelf | Name | Email | Password |
| --- | --- | --- | --- |
| Lender, because she offered the copies | Amina Niyonsenga | amina.demo@courseshelf.example | shelf-demo-pass-2026 |
| Borrower | Jean Habimana | jean.demo@courseshelf.example | shelf-demo-pass-2026 |

There is no separate permission role in the database. The lender is the student who owns the copy. The borrower is the student who reserved it. Jean also owns two copies. He cannot reserve those, and neither can Amina reserve a copy she owns.

For the demo I sign in as Jean, reserve the available Clean Code copy offered by Amina, then sign in as Amina and confirm pickup and return on that same card. I leave the Introduction to Algorithms card alone. That copy is already on loan.

## The records I seed

Three courses and three pickup points:

- `DEMO-CS101`, Demonstration: Introduction to Programming. Pickup: Demo pickup: library steps (north).
- `DEMO-DS201`, Demonstration: Data Structures. Pickup: Demo pickup: lab block bench.
- `DEMO-WD301`, Demonstration: Web Infrastructure Workshop. Pickup: Demo pickup: student hub desk.

The editions come from real Open Library responses. I keep the cover when Open Library gives me one.

| ISBN-13 | Title | Why it is on the shelf |
| --- | --- | --- |
| 9780132350884 | Clean Code, Robert C. Martin | No edition name in the record, so the card says “Edition not stated”. Amina offers an available copy. This is the copy I reserve in the demo. Jean also has a spare copy of the same edition, which he cannot reserve himself. One older Clean Code loan is already in the history as returned. |
| 9780262033848 | Introduction to Algorithms, Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein | Already on loan. I leave this card alone during the demo. |
| 9780134685991 | Effective Java, Joshua Bloch | Available, offered by Amina. |
| 9780201633610 | Design Patterns, Erich Gamma, John Vlissides, Richard Helm, Ralph Johnson | Available, offered by Amina. |
| 9781449373320 | Designing Data-Intensive Applications, Martin Kleppmann | Available. A search for `Kleppmann` or `replication` finds this card. |
| 9780134494166 | Clean Architecture, Robert C. Martin | Available. This is a different book from Clean Code. |
| 9781492078005 | Head First Design Patterns, Eric Freeman and the other authors named by Open Library | Available. |
| 9780134757599 | Refactoring, Martin Fowler | Available. |
| 9780596517748 | JavaScript: The Good Parts, Douglas Crockford | Available. |
| 9780321573513 | Algorithms, Robert Sedgewick | Available. This is a different book from Introduction to Algorithms. |
| 9780262510875 | Structure and Interpretation of Computer Programs, Harold Abelson, Gerald Jay Sussman, Julie Sussman | Available. |
| 9781617292231 | Grokking Algorithms, Aditya Y. Bhargava | Jean’s copy. He cannot reserve it. |
| 9781718502703 | Python Crash Course, 3rd Edition, Eric Matthes | Available. |
| 9780201616224 | The Pragmatic Programmer, Andrew Hunt, Dave Thomas | Jean’s copy. He cannot reserve it. |
| 9780131103627 | The C Programming Language, Brian W. Kernighan, Dennis Ritchie | Available. |
| 9781492057611 | Learning SQL, Alan Beaulieu | Available. |
| 9781492032649 | Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow, Aurélien Géron | Available. |
| 9780735619678 | Code Complete, Steve McConnell | Available. This is a different book from Clean Code. |

Each card carries a note in the lender’s own words. I can run the seed again. It replaces the demonstration rows and does not leave a second open loan on the same copy.

Open Library sometimes repeats an author name in one record. I show the names the API returned.

## The Open Library API

Documentation: https://openlibrary.org/dev/docs/api/books

I use one documented request:

`GET https://openlibrary.org/api/books?bibkeys=ISBN:{isbn13}&format=json&jscmd=data`

Every request sends this User-Agent:

`CourseShelf/1.0 (Herve Friend KUBANA; +https://openlibrary.org/dev/docs/api/books)`

The client lives in `app/openlibrary.py`. Before the request, `app/core.py` removes spaces and hyphens, checks the ISBN-10 or ISBN-13 check digit, and turns a valid ISBN-10 into an ISBN-13. An ISBN that fails that check never leaves the machine. I send the ISBN only. I do not search Open Library by title, and I do not invent an edition when the record has none.

A successful response is stored in the `isbn_lookups` table, including the payload I received. The next lookup of that ISBN reads the cache. I do not cache a timeout, an HTTP 429, a network failure, or an empty record, so a later lookup is allowed to succeed. The timeout is `OPENLIBRARY_TIMEOUT_SECONDS`, and I set it to 6.

When the author field is missing I show “Author not listed”. When the edition name is missing I show “Edition not stated”. A cover is shown only when its address starts with `https://covers.openlibrary.org/`. Some of those addresses redirect to `archive.org`. The page allows those image hosts. If the image fails, the broken icon is hidden.

Book records and covers come from the Internet Archive Open Library. I credit that project here and in the footer of the application.

## Errors the student actually sees

| Situation | What I do | What the student sees |
| --- | --- | --- |
| ISBN fails the check digit, including `0` | I do not call Open Library. | The form keeps the typed ISBN and says it is not valid. |
| Open Library does not answer within 6 seconds | I do not cache the failure. | The form keeps every field and says Open Library did not answer in time. |
| Open Library returns HTTP 429 | I do not cache the failure. | The form keeps every field and asks the student to wait. |
| Open Library cannot be reached | I do not cache the failure. | The form keeps every field. The student can try again or publish the title and author already typed. |
| Open Library has no record | I do not cache the empty result. | The form stays as the student left it and says there is no record. |
| The record is missing an author or an edition | I keep the fields Open Library did send. | “Author not listed” or “Edition not stated”. |
| A guest tries to reserve, offer, pick up, return, or cancel | The route asks for a login. | The login page, then the original action. |
| The owner reserves their own copy | I reject the request. | A refusal. Another student can still reserve that copy. |
| Two students reserve one available copy at the same moment | The row is locked with `SELECT FOR UPDATE`. The copy changes to reserved only while it is still available. | One student gets the reservation. The other is told the copy is no longer available. |
| A second open loan is inserted for the same copy | The partial unique index `loans_one_open_per_copy` rejects it. | The copy keeps a single open loan. |
| The return-by date is today, in the past, or more than 120 days away | I reject the date. | The student is asked for a date after today and within 120 days. |
| A POST form arrives without the session token | I compare the token with `secrets.compare_digest`. | The action is rejected. |
| The note is longer than 280 characters | I reject the note. | The student is asked to shorten it. |
| The database cannot be reached | `/healthz` reports it. | The health body says the database is not ok. |

SQL is sent with parameters through psycopg. I do not build a query by joining the student’s text into the SQL string.

## Loan rules

The clock is Africa/Kigali. I show a date as `24 Nov 2026`. The default return-by date is 14 days after the campus today. A reservation is accepted only when the date is after that day and within 120 days.

The life of a copy is available, then reserved, then on loan, then available again. The loan row is kept after the return, with the status returned. A cancelled reservation is also kept, with the status cancelled. The open states are reserved and picked up. The index allows only one of those per copy.

Confirm pickup is the lender’s action. Confirm return is the lender’s action. Cancel is available to the borrower or the lender before pickup. I do not let the owner become the borrower of their own copy.

## The stack I pinned

I pinned these versions on 22 Nov 2026 from my own `pip freeze` on Python 3.14.6, macOS arm64. `requirements.txt` installs these exact versions.

| Package | Version | What I use it for |
| --- | --- | --- |
| Flask | 3.1.3 | Routes, sessions, and the application factory |
| Jinja2 | 3.1.6 | The HTML templates |
| Werkzeug | 3.1.9 | Password hashes and the signed cookie |
| Gunicorn | 27.0.1 | The application server on web-01 and web-02 |
| psycopg | 3.3.9 | PostgreSQL, with parameters |
| psycopg-binary | 3.3.9 | The PostgreSQL wheel for this machine |
| python-dotenv | 1.2.4 | `.env`, without overriding a value I already set in the shell |

PostgreSQL is version 16. On my Mac I do not set a database password. `DATABASE_URL=postgresql:///courseshelf` uses the local socket.

The interface is my own HTML, Jinja, and one plain stylesheet. I use the browser’s system font. I do not load a CSS framework or a font file. The pages still render when the machine is offline, apart from a cover that has not been cached by the browser.

`.gitignore` excludes `.env`, `.venv`, `__pycache__`, logs, and the local database directory. I never commit a secret.

## How I run it on my Mac

I need Python 3.12 or newer, PostgreSQL 16, and a browser. I developed on Python 3.14.6. The PostgreSQL tools on my Mac are in `/opt/homebrew/opt/postgresql@16/bin`.

From the repository root:

```bash
git clone https://github.com/Kubanaherve/courseshelf.git
cd courseshelf
bash scripts/setup.sh
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
createdb courseshelf || true
.venv/bin/python scripts/migrate.py
.venv/bin/python scripts/seed.py
```

`scripts/setup.sh` creates `.venv`, installs `requirements.txt`, and copies `.env.example` to `.env` only when `.env` does not already exist. I then put two values into `.env`.

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

That command prints the 64-character hex value I put in `SECRET_KEY`. I set `DEMO_STUDENT_PASSWORD=shelf-demo-pass-2026`. I leave `FLASK_DEBUG=0`. I leave `APP_ENV=local` on my Mac. If `createdb` says the database already exists, the database is already there and I continue.

I start the shelf and I leave the Terminal window open:

```bash
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
.venv/bin/flask --app wsgi run --host 127.0.0.1 --port 5050
```

I open http://127.0.0.1:5050/. If the port is already in use, the shelf is already running.

| Name | Local value | What reads it |
| --- | --- | --- |
| `APP_ENV` | `local` on my Mac, `production` on the public servers | The application refuses a production boot when debug is on or the secret is still a placeholder |
| `FLASK_DEBUG` | `0` | Flask |
| `SECRET_KEY` | 64 hex characters, the same value on web-01 and web-02 | The signed session cookie |
| `DATABASE_URL` | `postgresql:///courseshelf` on my Mac | psycopg |
| `BACKEND_NAME` | `local` on my Mac | The footer and `X-CourseShelf-Backend` |
| `BIND_HOST` | `127.0.0.1` | The local listener |
| `PORT` | `5050` | The local shelf. macOS often holds port 5000 |
| `SESSION_COOKIE_SECURE` | `0` | The cookie is still set on the local HTTP shelf |
| `OPENLIBRARY_TIMEOUT_SECONDS` | `6` | The Open Library client |
| `OPENLIBRARY_USER_AGENT` | the User-Agent in the API section | The outbound request |
| `DEMO_STUDENT_PASSWORD` | `shelf-demo-pass-2026` | The seed, when it hashes the two accounts |

A value I export in the shell wins over the same name in `.env`. That is how web-01 and web-02 can share one database URL and still send different backend names. I do not publish `SECRET_KEY`, and I do not publish a database password.

## How I test the local shelf

```bash
curl -sS http://127.0.0.1:5050/healthz
```

I expect HTTP 200 and:

```json
{"backend":"local","database":"ok","status":"ok"}
```

I then follow this path in the browser.

1. I open http://127.0.0.1:5050/ and I expect the heading Course shelf, the name Herve Friend KUBANA, and Clean Code.
2. I search `9780132350884` and I expect Clean Code. I search `Kleppmann` and I expect Designing Data-Intensive Applications. I clear the search and the rest of the shelf returns.
3. I open Offer while signed out and I expect the login page.
4. I sign in as `jean.demo@courseshelf.example` with `shelf-demo-pass-2026`. I look up `9780132350884`. I expect Clean Code and Robert C. Martin, and I expect the edition box to stay empty. I do not publish another copy during this check.
5. I try ISBN `0`. I expect the invalid-ISBN error, and I expect the form to keep what I typed.
6. I return to the shelf and reserve the available Clean Code card offered by Amina Niyonsenga. I leave the return-by date as it is. I do not reserve the Clean Code card offered by Jean Habimana.
7. Loans shows that reservation as waiting for pickup.
8. I sign out, sign in as `amina.demo@courseshelf.example` with the same password, and on the Clean Code card whose borrower is Jean I click Confirm pickup and then Confirm return. The history says returned. I do not touch Introduction to Algorithms.
9. I reserve another available copy as Jean and I cancel it before pickup. The copy is available again.

## The lab I use in the video

I did not create new servers. The video uses the Web Infrastructure lab containers that are already on my Mac: web-01, web-02, and lb-01.

- web-01 is http://127.0.0.1:8080/. Its Nginx proxies to Gunicorn on port 8001. I start that Gunicorn with `BACKEND_NAME=web01`. The response header `X-CourseShelf-Backend` is `web01`. A direct request to port 8080 does not include `X-Served-By`.
- web-02 is http://127.0.0.1:8081/. Its Nginx proxies to Gunicorn on port 8002. I start that Gunicorn with `BACKEND_NAME=web02`. The header is `web02`. A direct request to port 8081 does not include `X-Served-By`.
- lb-01 is http://127.0.0.1:8082/. HAProxy round-robins between those two servers. After HAProxy chooses a server, it adds `X-Served-By`. Refreshing port 8082 moves `X-Served-By` between `web-01` and `web-02`, and moves `X-CourseShelf-Backend` between `web01` and `web02`. One refresh can repeat the same server. I refresh until both names have appeared. The footer shows the same backend name as `X-CourseShelf-Backend`. The header is the signal I trust, because the page cannot invent a header that only the load balancer adds.

Both lab servers read the PostgreSQL database on my Mac, and both use the same `SECRET_KEY`. A reservation made through port 8080 is visible through port 8081. The containers do not include PostgreSQL. The lab TLS certificate is the existing file `/etc/ssl/certs/ha_proxy_ssl.pem`. Let's Encrypt cannot see `127.0.0.1`, so I did not request a certificate for the lab. Port 8082 answers on HTTP.

```bash
curl -sSI http://127.0.0.1:8080/healthz
curl -sSI http://127.0.0.1:8081/healthz
curl -sSI http://127.0.0.1:8082/healthz
```

The first two commands show `X-CourseShelf-Backend` and no `X-Served-By`. The third command shows both headers.

These three addresses run on my Mac. When I shut the Mac down, ports 5050, 8080, 8081, and 8082 stop. I record the video while the Mac is on.

## The website I submit

The address a reviewer opens is https://www.friendherve.tech. I did not change the DNS records. The name `www` already points at the load balancer. HAProxy accepts HTTPS with the certificate issued for `www.friendherve.tech` and round-robins each request to web-01 and web-02 on port 80. The certificate is for `www`. I publish the `www` address for that reason.

On each public web server:

- The code is in `/opt/courseshelf`.
- systemd runs the `courseshelf` service as the user `ubuntu`.
- Gunicorn binds to `127.0.0.1:8000` with one worker. The worker count stays at one because these machines are small.
- `BACKEND_NAME` is `web01` on the first server and `web02` on the second.
- Nginx 1.18 receives the public request and proxies the CourseShelf hostnames to that Gunicorn.
- Nginx adds `X-Served-By` with the machine name, `7329-web-01` or `7329-web-02`.
- The application adds `X-CourseShelf-Backend` with `web01` or `web02`.
- The footer shows that same backend name.
- Both servers read one PostgreSQL 16 database and one shared `SECRET_KEY`. The environment file stays on the server. It is not in this repository.
- PostgreSQL runs on web-01. web-02 reaches it through an SSH tunnel to `127.0.0.1:5432`. I do not open port 5432 to the internet, and I do not install a second PostgreSQL on web-02.
- A request to a raw server address still returns Holberton School. That default site stays in place, including its redirect and its 404 page. CourseShelf is served for its own hostnames.

I check the public balance with:

```bash
curl -sSI https://www.friendherve.tech/healthz
curl -sS https://www.friendherve.tech/healthz
```

The header command shows `X-Served-By: 7329-web-01` or `X-Served-By: 7329-web-02`, and `X-CourseShelf-Backend: web01` or `X-CourseShelf-Backend: web02`. The body looks like:

```json
{"backend":"web01","database":"ok","status":"ok"}
```

The backend value changes between `web01` and `web02` across requests. The public site does not use my Mac. After I close the laptop, https://www.friendherve.tech still answers, as long as those servers are up.

## Problems I met, and what I changed

- Open Library’s documentation page timed out while I was mapping the fields. I kept a real Books API response and mapped the title, authors, edition, date, publishers, cover, and Open Library key from that response. I still send only a checked ISBN.
- A title is not an edition. When the record has no edition name, the screen says “Edition not stated”. I do not fill the box from the title.
- Some cover addresses redirect from `covers.openlibrary.org` to `archive.org`, and then to an `archive.org` image host. The page allows those hosts. An image that fails to load is hidden, so the card does not keep a broken-image icon.
- macOS often holds port 5000. The local shelf listens on port 5050, and the README, `.env.example`, and the run command all use that port.
- The lab containers do not include PostgreSQL. The lab database stays on my Mac, and both Gunicorn processes use it. On the public servers, PostgreSQL stays on web-01. web-02 uses an SSH tunnel to `127.0.0.1:5432`. I do not publish port 5432.
- Let's Encrypt cannot see `127.0.0.1`. The lab keeps the certificate that was already installed for HAProxy. The public name uses the certificate that was already issued for `www.friendherve.tech`.
- Two students can press Reserve at the same moment. The reservation updates the copy only while its status is still available, inside a transaction, with `SELECT FOR UPDATE`. The partial unique index stops a second open loan on that copy.
- The Open Library module must be named `app/openlibrary.py`, with a lowercase L. Python does not import a file named `openLibrary.py`.
- The first `bash scripts/setup.sh` failed because my Mac could not resolve `pypi.org`. I ran the same script again when the network answered. The message `database "courseshelf" already exists` means the database was created earlier. I continue.
- The raw IP of each web server still has to answer the Holberton School checks. CourseShelf is a second Nginx site, matched by hostname. The default site is unchanged.
- A browser that had previously opened the domain kept the old Holberton page. The application responses send `Cache-Control: no-store`. A hard refresh is Command+Shift+R.
- The signed cookie has to survive a round robin. web-01 and web-02 use the same `SECRET_KEY` and the same database, so the session remains valid when the next request reaches the other server.

## The files in this repository

```text
wsgi.py                     I start the app from here
app/__init__.py             the application factory, security headers, and error pages
app/core.py                 the database, ISBN checks, campus dates, and login
app/openlibrary.py          the Open Library client and the success cache
app/loans.py                search, publish, reserve, pickup, return, and cancel
app/routes.py               the three screens and the health check
app/templates/              shelf, offer, loans, login, and the error page
migrations/001_schema.sql   the tables and the one-open-loan index
scripts/setup.sh            the virtualenv and the pinned install
scripts/migrate.py          applies the SQL, and can be run again
scripts/seed.py             the two accounts, the editions, and the copies
requirements.txt            the pinned packages
.env.example                the names I set, with no real secret
.gitignore                  keeps .env and the virtualenv out of Git
README.md                   this file
```

## Credit

Developed by Herve Friend KUBANA.

Book records and covers come from the Internet Archive Open Library: https://openlibrary.org/dev/docs/api/books

I used Flask, Jinja, Werkzeug, Gunicorn, psycopg, PostgreSQL, Nginx, and the HAProxy already installed on the load balancer.
