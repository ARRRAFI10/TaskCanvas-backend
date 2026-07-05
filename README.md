# TaskCanvas — Backend

Django 5 + Django REST Framework API powering **TaskCanvas**: a 2-in-1 task
management (Kanban) and image annotation app. The Next.js frontend lives in a
separate repository (`taskcanvas-frontend`).

> Full documentation (villains faced, versions, deployment guide) lands with the
> final phase. Quick start for now:

```bash
python -m venv venv
venv\Scripts\pip install -r requirements/dev.txt
venv\Scripts\python manage.py migrate
venv\Scripts\python manage.py runserver
```

API health check: `GET http://127.0.0.1:8000/api/health/`
