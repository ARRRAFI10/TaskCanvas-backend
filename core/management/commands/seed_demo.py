"""Create (or reset) the demo account with a spread of sample tasks."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tasks.models import Tag, Task

DEMO_EMAIL = "demo@taskcanvas.app"
DEMO_PASSWORD = "TaskCanvas#2026"

TODO, DOING, DONE = Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.DONE
LOW, MED, HIGH, URGENT = (
    Task.Priority.LOW,
    Task.Priority.MEDIUM,
    Task.Priority.HIGH,
    Task.Priority.URGENT,
)

# (day offset, status, priority, title, tags)
SAMPLE_TASKS = [
    (-1, DONE, HIGH, "Ship annotation API endpoints", ["backend", "api"]),
    (-1, DONE, MED, "Review chest X-ray batch #42", ["imaging", "review"]),
    (0, TODO, URGENT, "Label CT slices — lung nodule set", ["imaging", "ml"]),
    (0, TODO, MED, "Write polygon drawing hook", ["frontend", "canvas"]),
    (0, DOING, HIGH, "Fix drag-and-drop rollback on error", ["frontend", "bug"]),
    (0, DOING, LOW, "Refactor date selector props", ["frontend"]),
    (0, DONE, MED, "Sync design tokens with Figma", ["design"]),
    (1, TODO, HIGH, "Prepare demo video script", ["docs"]),
    (1, TODO, MED, "QA pass on upload validation", ["backend", "review"]),
    (1, DOING, MED, "Annotate MRI benchmark set", ["imaging", "ml"]),
    (2, TODO, LOW, "Clean up unused Tailwind tokens", ["frontend", "design"]),
    (2, TODO, MED, "Draft deployment checklist", ["docs", "devops"]),
]


class Command(BaseCommand):
    help = "Create the demo user and reset their board with sample tasks (idempotent)."

    def handle(self, *args, **options):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            email=DEMO_EMAIL, defaults={"first_name": "Demo", "last_name": "User"}
        )
        user.set_password(DEMO_PASSWORD)
        user.save()

        user.tasks.all().delete()
        today = timezone.localdate()
        positions: dict[tuple, int] = {}
        for offset, status, priority, title, tag_names in SAMPLE_TASKS:
            due = today + timedelta(days=offset)
            position = positions.get((due, status), 0)
            positions[(due, status)] = position + 1
            task = Task.objects.create(
                user=user,
                title=title,
                status=status,
                priority=priority,
                due_date=due,
                position=position,
            )
            task.tags.set(Tag.objects.get_or_create(user=user, name=name)[0] for name in tag_names)

        verb = "Created" if created else "Reset"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} demo account with {len(SAMPLE_TASKS)} tasks.\n"
                f"  email:    {DEMO_EMAIL}\n"
                f"  password: {DEMO_PASSWORD}"
            )
        )
