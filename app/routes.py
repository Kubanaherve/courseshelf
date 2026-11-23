"""I serve my three screens from here, plus login and my health check."""

from functools import wraps

from flask import flash, redirect, render_template, request, session, url_for

from app.core import (
    AVAILABILITY_OPTIONS,
    DEMO_COURSES,
    DEMO_LANDMARKS,
    SORT_OPTIONS,
    authenticate,
    connection,
    course_name,
    current_student,
    default_return_by,
    ensure_csrf_token,
    known_landmark,
    normalize_isbn,
    parse_return_by,
    rotate_session,
    safe_next_path,
)
from app.loans import (
    cancel_reservation,
    confirm_pickup,
    confirm_return,
    loans_for_student,
    publish_copy,
    reserve_copy,
    search_copies,
)
from app.openlibrary import lookup_isbn


def register_routes(app):
    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("student_id") is None:
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        return wrapped

    @app.context_processor
    def inject_shell():
        student = None
        try:
            student = current_student()
        except Exception:
            app.logger.exception("could not load the signed-in student")
        return {
            "student": student,
            "csrf": ensure_csrf_token(),
            "backend_name": app.config.get("BACKEND_NAME", "local"),
            "courses": DEMO_COURSES,
            "landmarks": DEMO_LANDMARKS,
        }

    @app.get("/")
    def shelf():
        course = request.args.get("course", "")
        availability = request.args.get("availability", "")
        query = request.args.get("q", "")
        sort = request.args.get("sort", "title")
        if course and course_name(course) is None:
            course = ""
        copies = search_copies(course, availability, query, sort)
        return render_template(
            "shelf.html",
            active="shelf",
            copies=copies,
            course=course,
            availability=availability if availability in ("available", "reserved", "on_loan") else "",
            query=query,
            sort=sort if sort in ("title", "return_by") else "title",
            availability_options=AVAILABILITY_OPTIONS,
            sort_options=SORT_OPTIONS,
            default_return=default_return_by().isoformat(),
            min_return=_shift_days(1),
            max_return=_shift_days(120),
        )

    @app.get("/offer")
    @login_required
    def offer():
        return render_template("offer.html", active="offer", form=_empty_offer(), errors={})

    @app.post("/offer")
    @login_required
    def offer_submit():
        student = current_student()
        form = {
            "isbn": request.form.get("isbn", ""),
            "title": request.form.get("title", ""),
            "authors": request.form.get("authors", ""),
            "edition_label": request.form.get("edition_label", ""),
            "course_code": request.form.get("course_code", ""),
            "pickup_landmark": request.form.get("pickup_landmark", ""),
            "note": request.form.get("note", ""),
        }
        errors = {}
        isbn13 = normalize_isbn(form["isbn"])
        if not isbn13:
            errors["isbn"] = (
                "That ISBN check digit does not match. Enter the 10 or 13 digit ISBN "
                "printed on the copyright page."
            )

        action = request.form.get("action", "publish")
        if action == "lookup":
            if isbn13 and "isbn" not in errors:
                result = lookup_isbn(isbn13)
                if result.ok:
                    form["title"] = result.fields.get("title") or form["title"]
                    form["authors"] = result.fields.get("authors") or form["authors"]
                    if result.fields.get("edition_label"):
                        form["edition_label"] = result.fields["edition_label"]
                    form["cover_url"] = result.fields.get("cover_url")
                    form["publish_date"] = result.fields.get("publish_date") or ""
                    flash(result.message, "success")
                else:
                    errors["lookup"] = result.message
                    if result.fields:
                        if not form["title"]:
                            form["title"] = result.fields.get("title", "")
                        if not form["authors"]:
                            form["authors"] = result.fields.get("authors", "")
            return render_template("offer.html", active="offer", form=form, errors=errors), 200 if not errors else 422

        if errors:
            return render_template("offer.html", active="offer", form=form, errors=errors), 422

        name = course_name(form["course_code"])
        if name is None:
            errors["course_code"] = "Choose one of the demonstration courses."
        if not known_landmark(form["pickup_landmark"]):
            errors["pickup_landmark"] = "Choose one of the demonstration pickup landmarks."
        if len(form["note"]) > 280:
            errors["note"] = "Keep the note to 280 characters or fewer."
        if len(form["title"].strip()) > 300:
            errors["title"] = "Keep the title to 300 characters or fewer."
        if len(form["authors"].strip()) > 300:
            errors["authors"] = "Keep the author line to 300 characters or fewer."
        if len(form["edition_label"].strip()) > 120:
            errors["edition_label"] = "Keep the edition to 120 characters or fewer."
        if errors:
            return render_template("offer.html", active="offer", form=form, errors=errors), 422

        copy_id, message = publish_copy(
            student["id"],
            isbn13,
            form["title"],
            form["authors"],
            form["edition_label"],
            form["course_code"],
            name,
            form["pickup_landmark"],
            form["note"].strip(),
        )
        if copy_id is None:
            errors["title"] = message
            return render_template("offer.html", active="offer", form=form, errors=errors), 422
        flash(message, "success")
        return redirect(url_for("shelf", q=isbn13)), 303

    @app.get("/loans")
    @login_required
    def loans():
        student = current_student()
        groups = loans_for_student(student["id"])
        return render_template("loans.html", active="loans", **groups)

    @app.post("/reserve")
    @login_required
    def reserve():
        student = current_student()
        try:
            copy_id = int(request.form.get("copy_id", ""))
        except ValueError:
            flash("Choose a copy from the shelf.", "error")
            return redirect(url_for("shelf")), 303
        return_by, date_error = parse_return_by(request.form.get("return_by", ""))
        if date_error:
            flash(date_error, "error")
            return redirect(url_for("shelf")), 303
        result = reserve_copy(student["id"], copy_id, return_by)
        flash(result.message, "success" if result.ok else "error")
        return redirect(url_for("loans" if result.ok else "shelf")), 303

    @app.post("/loans/<int:loan_id>/pickup")
    @login_required
    def pickup(loan_id):
        student = current_student()
        result = confirm_pickup(student["id"], loan_id)
        flash(result.message, "success" if result.ok else "error")
        return redirect(url_for("loans")), 303

    @app.post("/loans/<int:loan_id>/return")
    @login_required
    def return_copy(loan_id):
        student = current_student()
        result = confirm_return(student["id"], loan_id)
        flash(result.message, "success" if result.ok else "error")
        return redirect(url_for("loans")), 303

    @app.post("/loans/<int:loan_id>/cancel")
    @login_required
    def cancel(loan_id):
        student = current_student()
        result = cancel_reservation(student["id"], loan_id)
        flash(result.message, "success" if result.ok else "error")
        return redirect(url_for("loans")), 303

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            if session.get("student_id"):
                return redirect(safe_next_path(request.args.get("next")) or url_for("shelf"))
            return render_template("login.html", active="login", email="", error=None, next_path=request.args.get("next", ""))

        email = request.form.get("email", "")
        password = request.form.get("password", "")
        student_id = authenticate(email, password)
        if student_id is None:
            return (
                render_template(
                    "login.html",
                    active="login",
                    email=email,
                    error="Those demonstration credentials were not recognized.",
                    next_path=request.form.get("next", ""),
                ),
                401,
            )
        rotate_session(student_id)
        destination = safe_next_path(request.form.get("next", "")) or url_for("shelf")
        return redirect(destination), 303

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You are logged out of the demonstration shelf.", "success")
        return redirect(url_for("shelf")), 303

    @app.get("/healthz")
    def healthz():
        database = "unavailable"
        try:
            with connection() as conn:
                conn.execute("SELECT 1").fetchone()
            database = "ok"
        except Exception:
            app.logger.exception("health check failed")
        status = "ok" if database == "ok" else "degraded"
        body = {
            "status": status,
            "database": database,
            "backend": app.config.get("BACKEND_NAME", "local"),
        }
        return body, 200 if database == "ok" else 503


def _empty_offer():
    return {
        "isbn": "",
        "title": "",
        "authors": "",
        "edition_label": "",
        "course_code": "",
        "pickup_landmark": "",
        "note": "",
        "cover_url": None,
        "publish_date": "",
    }


def _shift_days(days):
    from datetime import timedelta

    from app.core import campus_today

    return (campus_today() + timedelta(days=days)).isoformat()
