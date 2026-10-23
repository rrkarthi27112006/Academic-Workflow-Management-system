# EduTrack — Student Academic Task & Progress Platform

A Django web app for schools: teachers assign academic work, students track
and submit it, teachers grade and give feedback, and parents watch progress —
all with plain Django templates, custom CSS, and zero JavaScript.

## Tech stack

Python, Django, Django ORM, Django's built-in auth, Django Templates,
HTML5, custom CSS3, SQLite. No Bootstrap/Tailwind/React/jQuery/JS anywhere —
every interaction (filtering, forms, navigation) is a normal Django page
request. The notifications dropdown uses a native `<details>` element, not
JavaScript.

## Project structure

```
edutrack/
    manage.py
    edutrack/          settings.py, urls.py, wsgi.py
    accounts/          User roles: TeacherProfile, StudentProfile, ParentProfile; auth
    academics/         School, ClassRoom, Subject; class/subject/student management
    tasks/             Task & Submission models + Smart Priority System + submit & review flows
    notifications/     Notification + Announcement models, in-app notifications
    dashboard/         Landing page, role dashboards, workload/progress/report logic
    templates/         base.html (shared shell: sidebar, topbar, notifications)
    static/css/        style.css (single stylesheet, custom design system)
    media/             uploaded task attachments and student submissions
```

Each app has its own `models.py`, `views.py`, `forms.py`, `urls.py`,
`admin.py`, and a `templates/<app_name>/` folder — nothing is dumped into one
giant file.

## Key features implemented

- **Roles**: Teacher, Student, Parent, each with their own dashboard and
  role-based access control (a student cannot open a teacher URL — it
  returns 403; parents are read-only).
- **Smart Priority System** (`tasks/models.py` — `Task.smart_priority_*`):
  scores each task from time remaining, difficulty, estimated effort, marks,
  and teacher-set importance, then labels it HIGH / MEDIUM / LOW and writes a
  one-sentence reason, shown in the student's "What Should I Work On First?"
  section.
- **Deadline Conflict Alert** and **Missed Task Warning**
  (`dashboard/services.py`): flags a heavy workload when multiple demanding
  tasks cluster within 24 hours, and warns when a student has repeatedly
  missed deadlines.
- **Workload analysis, subject-wise progress, and teacher reports**, all
  computed with plain Python/Django — no AI, no external APIs.
- Task types, difficulty, importance, file/image submissions, resubmission
  control, marks & feedback, announcements, and an in-app notification feed.

## Demo accounts (seeded automatically)

| Role    | Username       | Password   |
|---------|----------------|------------|
| Teacher | `anitha`       | `demo1234` |
| Student | `rahul`        | `demo1234` |
| Student | `priya`        | `demo1234` |
| Parent  | `rahul_parent` | `demo1234` |
| Admin   | `admin`        | `admin1234`|

The seed data includes class **10-A**, subjects **Mathematics, Science,
English, Computer Science**, and six sample tasks with different due dates,
difficulty levels, effort estimates and marks — enough to see HIGH, MEDIUM
and LOW smart-priority tasks side by side on Rahul's dashboard.

## Setup (Windows, Command Prompt)

```bat
:: 1. Unzip the project, then open a terminal inside the edutrack folder

:: 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

:: 3. Install Django
pip install django

:: 4. Apply migrations (the database is already included and seeded,
::    but this is safe to re-run and needed if you delete db.sqlite3)
python manage.py migrate

:: 5. (Optional) create your own superuser instead of using the seeded one
python manage.py createsuperuser

:: 6. (Optional) re-seed demo data — safe to run again, it won't duplicate
python manage.py seed_demo_data

:: 7. Run the project
python manage.py runserver
```

Then open **http://127.0.0.1:8000/** in your browser. Log in with any of
the demo accounts above, or register a new Student/Teacher account from the
landing page.

Admin site: **http://127.0.0.1:8000/admin/**

## Notes

- `db.sqlite3` ships pre-seeded, so you can run the app immediately after
  `pip install django` without any extra setup.
- Uploaded files (task attachments, student submissions) are validated for
  type (PDF, DOC, DOCX, PPT, PPTX, JPG, PNG) and size (max 10 MB) in
  `submissions/forms.py`.
- Parent accounts are created by a teacher/admin (via `/admin/`) and linked
  to a student through `StudentProfile.parent` — parents don't self-register,
  matching the brief.
