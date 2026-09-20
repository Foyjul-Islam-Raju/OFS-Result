# OFS Result System

A Student Result Management System for Online Foundation School, built with Django 5,
Bootstrap 5 and Django templates. Students look up a result with **Student ID + Class only** —
no password, no PIN.

---

## 1. Run it on Windows (PowerShell + VS Code)

Open the project folder in VS Code, then in the PowerShell terminal:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

If PowerShell blocks the activate script, run this once:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then open:

| Page | URL |
| --- | --- |
| Student portal | http://127.0.0.1:8000/ |
| Staff sign in | http://127.0.0.1:8000/login/ |
| Admin dashboard | http://127.0.0.1:8000/manage/ |
| Django admin | http://127.0.0.1:8000/django-admin/ |

Demo login for the portal: Student ID `6001`, class `Class 6`.

Run the tests:

```powershell
python manage.py test
```

---

## 2. Everyday admin workflow

1. **Classes** → add Play Group … Class 10.
2. **Sections** → optional. Skip this if your school does not use A/B/C.
3. **Subjects** → Bangla, English, Mathematics, Science, ICT.
4. **Class subjects** → tick the subjects each class studies. Class 6 six of them, Class 9 ten.
5. **Exam types** → "Class Examination" (plain), and "Semester Examination" with the semester switch on.
6. **Semesters** → only if you run semester exams.
7. **Exams** → e.g. "2nd Tutorial Examination", year 2026, and pick its type.
8. **Exam setup** → loads the class curriculum; untick anything this exam was not held in, adjust full marks.
9. **Students** → add students with a unique Student ID.
10. **Mark entry** → pick exam + class (+ section), type obtained marks, tick *Absent* where needed, **Save draft**.
11. **Review & publish** → check totals, percentages, grades, subject-wise highest marks, then **Publish result**.
12. Students can now see it. **Unpublish** hides it again instantly.

Percentages, totals, highest marks, GPA and CGPA are never typed by hand.

---

## 3. Dynamic subjects

Nothing assumes a fixed number of subjects. A class studies as many subjects as
there are rows in **Class subjects**, and an exam covers as many as you tick in
**Exam setup**. Class 6 with six subjects and Class 9 with ten run on the same
result engine, and growing Class 6 to ten subjects next year is a data change,
not a code change.

Two separate lists, on purpose:

* **Class subjects** — the curriculum. What the class studies all year.
* **Exam setup** — which of those subjects this particular exam was held in.

A subject only reaches a student's result if it appears in the second list, so
an exam that skipped Religion simply shows the other subjects.

---

## 4. How results are calculated

All of this lives in `results/grading.py` and `results/services.py`. Nothing is
duplicated elsewhere.

```
Subject percentage = obtained / full_mark * 100
Average percentage = total obtained / total full * 100
```

What a result shows depends on the exam's **type**, which you control from the
admin panel:

| Exam type | Result shows |
| --- | --- |
| Regular / class exam | Subject marks · Total · Average percentage · Pass/Fail |
| Semester examination | The same, plus letter grades, semester GPA and CGPA |

A regular class exam shows no letter grades and no GPA — just the marks, the
total, the percentage and whether the student passed. An exam with no type set
is treated as a regular class exam.

**GPA and CGPA** apply only to semester examinations. GPA is credit-weighted
across the subjects of that semester; CGPA is credit-weighted across every
semester the student has sat so far, so semesters with different subject counts
still combine correctly. Grade points come from the percentage:

| Percentage | Grade | Point |
| --- | --- | --- |
| 80–100 | A+ | 5.00 |
| 70–79 | A | 4.00 |
| 60–69 | A- | 3.50 |
| 50–59 | B | 3.00 |
| 40–49 | C | 2.00 |
| 33–39 | D | 1.00 |
| below 33 | F | 0.00 |

Because the point comes from the percentage, 64 out of 80 is 80% → 5.00, while
64 out of 100 is 64% → 3.50.

**Passing criteria** are configurable in two places: per exam (the Pass
percentage field on the exam) and school-wide under Settings. The per-exam value
wins when it is set. You can also require a pass in every subject, decide whether
absence fails a result, and decide whether failing a subject drops GPA to 0.00.

**Absent** is stored as a flag, not as a zero. An absent subject shows "Absent",
is excluded from the highest-mark calculation, and (by default) counts as a failed subject.

**Highest mark** is a live `MAX()` over the marks table, scoped to the same
exam + class + subject (+ section when section-wise mode is on). Ties are fine —
the review page shows every student who hit the top score.

**Pass rule** is configurable under Settings: pass percentage, whether every
subject must be passed, and whether absence fails the result.

**Position** is off by default. Turn it on in Settings to show class position.

---

## 5. Security model

* Every `/manage/...` page requires a signed-in staff user.
* A student proves identity by submitting Student ID **and** Class together.
  The verified student's primary key goes into the session; result pages read it
  from the session, never from the URL. Editing the URL cannot show someone else's result.
* Publication state is re-checked server-side on every single request.
* Draft results are never rendered.
* All mark validation runs on the server; the JavaScript checks are a convenience only.
* CSRF protection on every form. Secure cookies and HSTS switch on automatically when `DJANGO_DEBUG=False`.

---

## 6. Project layout

```
config/      settings, urls, wsgi/asgi
academics/   ClassRoom, Section, Subject, ClassSubject, ExamType, Semester,
             Exam, ExamSubject + CRUD and the exam setup screen
students/    Student + CRUD
results/     Mark, ResultPublication, grading.py, services.py,
             admin mark entry/review/publish, student portal, tests, seed_demo
dashboard/   SiteSetting, statistics dashboard, settings screen
templates/   base_admin.html, base_portal.html, partials/, portal/, ...
static/      css/theme.css, js/app.js, images/logo.png
```

---

## 7. Deploying

### Netlify — not possible

Netlify only hosts static files and JavaScript functions. It cannot run Django.
Use one of the options below instead.

### Render (recommended)

`render.yaml` is included. Push the repo to GitHub, create a Render Blueprint from it,
and Render provisions PostgreSQL, runs migrations and starts gunicorn. Then open the
Render shell and run `python manage.py createsuperuser`.

### Vercel

`vercel.json` and `build_files.sh` are included, but read this first:

Vercel functions have a **read-only, throwaway filesystem**, so SQLite will not work —
every mark you save would vanish. You must attach an external Postgres database
(Neon, Supabase and Railway all have free tiers).

1. Create a Postgres database and copy its connection string.
2. Push this project to GitHub and import it in Vercel.
3. In Vercel → Settings → Environment Variables add:
   * `DJANGO_SECRET_KEY` — a long random string
   * `DJANGO_DEBUG` — `False`
   * `DJANGO_ALLOWED_HOSTS` — `.vercel.app`
   * `DATABASE_URL` — `postgres://user:pass@host/db?sslmode=require`
4. Deploy.
5. Run the migrations once against that database from your own machine:

```powershell
$env:DATABASE_URL="postgres://user:pass@host/db?sslmode=require"
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
```

---

## 8. Common errors

| Message | Fix |
| --- | --- |
| `cannot be loaded because running scripts is disabled` | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `no such table: students_student` | You skipped `python manage.py migrate` |
| `NoReverseMatch` on a page | You are running an older copy of `urls.py`; re-copy the file |
| `UNIQUE constraint failed: students_student.student_id` | That Student ID already exists |
| `Obtained mark cannot be greater than Full Mark` | Working as intended — fix the mark or raise the full mark |
| Portal says "No result is available" | Marks exist but for a different exam, or no marks saved yet |
| Portal says "has not been published yet" | Publish it from **Review & publish** |
| Static files missing in production | `python manage.py collectstatic --noinput` |
