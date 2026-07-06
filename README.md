# TaskCanvas — Backend

Django 5 + Django REST Framework API powering **TaskCanvas**: a 2-in-1 task management
(Kanban) and image annotation app, built for the VaiRadiology fullstack engineering task.
The Next.js frontend lives in its own repository: **taskcanvas-frontend**.

| | |
|---|---|
| Live API | `https://<username>.pythonanywhere.com` *(link added after deploy)* |
| Frontend repo | `https://github.com/<you>/taskcanvas-frontend` |
| Live app | `https://<project>.vercel.app` |
| Demo login | `demo@taskcanvas.app` / `TaskCanvas#2026` |

## What this API does

- **Auth** — email + password JWT login (SimpleJWT): access/refresh pair, `/api/auth/me/`.
- **Tasks** — user-scoped CRUD with a `?date=` board filter, tags as plain string lists
  (`get_or_create`d per user), and an atomic `POST /move/` action that densely renumbers
  both affected Kanban columns inside a transaction.
- **Images** — multipart uploads validated for type (JPEG/PNG/WebP) and size (≤10 MB),
  with dimensions read by Pillow at upload time.
- **Annotations** — four shape types (polygon, rectangle, point, polyline) with
  per-shape point-count validation, stored as **normalized 0–1 coordinates** so drawings
  are resolution-independent. Full CRUD including PATCH for reshape/move/relabel/recolor.
- Everything is user-scoped — one user can never see or touch another user's rows —
  and every error shares one shape: `{"detail": "...", "errors": {field: [messages]}}`.

## Villains I faced (and how I beat them)

1. **The Python 3.14 compatibility scare.** My machine only had Python 3.14, newer than
   what most guides assume Django supports. Rather than downgrading blindly, I pinned
   Django to the 5.2 LTS line and verified with the official release notes (the power of
   friendship with documentation!) that recent 5.2 patches run on 3.14. The full test
   suite agreed.

2. **Drag-and-drop ordering, the shape-shifter.** Task positions looked trivial until
   deletes left gaps and concurrent moves could interleave. The fix: the `move/` endpoint
   rebuilds both affected columns as ordered lists and renumbers them densely inside
   `transaction.atomic()` with `bulk_update`, while plain creates append with
   `Max(position) + 1` so gaps can never cause collisions.

3. **Testing a 10 MB upload without a 10 MB image.** Generating a real >10 MB PNG in
   tests was slow and flaky. The trick that slew this villain: append padding bytes
   *after* the PNG's IEND chunk — Pillow still decodes it happily, but the file size
   crosses the limit, exercising the size validator honestly.

4. **One validator, four shapes.** When annotations grew from polygons to rectangles,
   points, and polylines, the point-count rule became shape-dependent — and PATCH
   requests don't always carry `shape_type`. The serializer's `validate()` now falls
   back to the instance's stored shape, so "reshape this rectangle with 3 points" is
   correctly rejected even when the request never mentions it's a rectangle.

5. **The exception handler that ate JWT errors.** My first global handler flattened
   SimpleJWT's `{"detail", "code"}` payloads into a generic "Validation failed". It now
   preserves `detail` whenever present and only wraps genuine field-error dictionaries.

## Versions & running locally

- **Python:** 3.14.5 (3.11–3.13 also fine; PythonAnywhere runs 3.13)
- **Django:** 5.2 LTS · **DRF:** 3.17 · **Database:** SQLite via Django ORM

```bash
git clone https://github.com/<you>/taskcanvas-backend.git
cd taskcanvas-backend

# 1. Virtual environment
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux

# 2. Dependencies (dev bundle includes ruff)
pip install -r requirements/dev.txt

# 3. Database + demo data
python manage.py migrate
python manage.py seed_demo       # creates demo@taskcanvas.app / TaskCanvas#2026 + sample tasks

# 4. Run
python manage.py runserver       # http://127.0.0.1:8000  (health: /api/health/)
```

No `.env` is required in development — sane defaults apply. For production every value
in `.env.example` must be set. CORS allows `http://localhost:3000` in dev.

**Tests** (43, covering auth, task CRUD/filter/move, upload validation, shape rules,
and cross-user isolation):

```bash
python manage.py test
```

**Lint:** `ruff check .`

## Deployment

Click-by-click PythonAnywhere instructions live in [DEPLOYMENT.md](DEPLOYMENT.md).
