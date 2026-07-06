# Deploying taskcanvas-backend to PythonAnywhere

PythonAnywhere is the right free host for this app because its filesystem is
**persistent** — uploaded images and the SQLite database survive restarts (unlike
Render/Railway free tiers, which wipe local disk on every deploy).

Your app will live at `https://<username>.pythonanywhere.com`.

## 1. Create the account

1. Sign up at https://www.pythonanywhere.com (free "Beginner" plan is enough).
2. Your username becomes your domain — choose accordingly.

## 2. Clone and set up (Bash console)

Open **Consoles → Bash** and run:

```bash
git clone https://github.com/<you>/taskcanvas-backend.git
cd taskcanvas-backend

mkvirtualenv --python=python3.13 taskcanvas
pip install -r requirements.txt        # resolves to requirements/prod.txt
```

## 3. Environment variables

The settings load a `.env` file from the project root. Create it:

```bash
cat > .env << 'EOF'
DJANGO_SECRET_KEY=<paste a long random string — python -c "import secrets; print(secrets.token_urlsafe(64))">
DJANGO_ALLOWED_HOSTS=<username>.pythonanywhere.com
CORS_ALLOWED_ORIGINS=https://<your-frontend>.vercel.app
EOF
```

> You can set `CORS_ALLOWED_ORIGINS` to a placeholder now and update it after the
> Vercel deploy hands you the real frontend URL — then hit **Reload** on the Web tab.

## 4. Database, demo user, static files

Still in the console (virtualenv active, inside `taskcanvas-backend`):

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py seed_demo
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py collectstatic --noinput
```

`seed_demo` prints the demo credentials (`demo@taskcanvas.app` / `TaskCanvas#2026`).

## 5. Create the web app (Web tab)

1. **Web → Add a new web app** → *Manual configuration* → **Python 3.13**.
2. **Source code:** `/home/<username>/taskcanvas-backend`
   **Working directory:** same path.
3. **Virtualenv:** `/home/<username>/.virtualenvs/taskcanvas`
4. **WSGI configuration file** (click the link, replace the whole file):

```python
import os
import sys

path = "/home/<username>/taskcanvas-backend"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
```

## 6. Static & media mappings (Web tab → Static files)

| URL | Directory |
|---|---|
| `/static/` | `/home/<username>/taskcanvas-backend/staticfiles` |
| `/media/` | `/home/<username>/taskcanvas-backend/media` |

## 7. HTTPS + reload

1. On the Web tab, enable **Force HTTPS**.
2. Click **Reload**.

## 8. Smoke test

```bash
curl https://<username>.pythonanywhere.com/api/health/
# → {"status": "ok"}

curl -X POST https://<username>.pythonanywhere.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@taskcanvas.app", "password": "TaskCanvas#2026"}'
# → {"refresh": "...", "access": "...", "user": {...}}
```

## Updating after a new git push

```bash
cd ~/taskcanvas-backend && git pull
workon taskcanvas && pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py collectstatic --noinput
```

…then **Reload** on the Web tab.
