from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Tag, Task

User = get_user_model()

DATE = "2026-07-05"


class TaskAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("a@example.com", "pass-12345")
        self.other = User.objects.create_user("b@example.com", "pass-12345")
        self.client.force_authenticate(self.user)

    def create_task(self, **overrides):
        payload = {"title": "Task", "due_date": DATE, "priority": "medium", "status": "todo"}
        payload.update(overrides)
        return self.client.post("/api/tasks/", payload, format="json")

    def column_ids(self, status, date=DATE):
        response = self.client.get(f"/api/tasks/?date={date}")
        return [t["id"] for t in response.data if t["status"] == status]

    # --- CRUD ---

    def test_list_requires_auth(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/tasks/").status_code, 401)

    def test_create_assigns_incrementing_positions(self):
        first = self.create_task(title="First")
        second = self.create_task(title="Second")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["position"], 0)
        self.assertEqual(second.data["position"], 1)

    def test_create_with_tags_dedupes_and_strips(self):
        response = self.create_task(tags=["Bug", " bug ", "ui"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["tags"], ["Bug", "ui"])
        self.assertEqual(Tag.objects.filter(user=self.user).count(), 2)

    def test_list_filters_by_date(self):
        self.create_task(title="Today")
        self.create_task(title="Tomorrow", due_date="2026-07-06")
        response = self.client.get(f"/api/tasks/?date={DATE}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([t["title"] for t in response.data], ["Today"])

    def test_invalid_date_returns_400(self):
        response = self.client.get("/api/tasks/?date=not-a-date")
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.data["errors"])

    def test_invalid_priority_rejected(self):
        response = self.create_task(priority="ultra")
        self.assertEqual(response.status_code, 400)
        self.assertIn("priority", response.data["errors"])

    def test_patch_replaces_tags(self):
        task_id = self.create_task(tags=["one", "two"]).data["id"]
        response = self.client.patch(f"/api/tasks/{task_id}/", {"tags": []}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tags"], [])

    def test_delete_task(self):
        task_id = self.create_task().data["id"]
        self.assertEqual(self.client.delete(f"/api/tasks/{task_id}/").status_code, 204)
        self.assertFalse(Task.objects.filter(pk=task_id).exists())

    # --- moving & ordering ---

    def test_status_change_via_patch_appends_to_target_column(self):
        self.create_task(title="Existing done", status="done")
        task_id = self.create_task(title="Now done").data["id"]
        response = self.client.patch(
            f"/api/tasks/{task_id}/", {"status": "done"}, format="json"
        )
        self.assertEqual(response.data["position"], 1)

    def test_move_within_column_reorders(self):
        ids = [self.create_task(title=f"T{i}").data["id"] for i in range(3)]
        response = self.client.post(
            f"/api/tasks/{ids[2]}/move/", {"status": "todo", "position": 0}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.column_ids("todo"), [ids[2], ids[0], ids[1]])

    def test_move_across_columns_renumbers_both(self):
        todo_ids = [self.create_task(title=f"T{i}").data["id"] for i in range(3)]
        doing_id = self.create_task(title="Doing", status="in_progress").data["id"]
        response = self.client.post(
            f"/api/tasks/{todo_ids[0]}/move/",
            {"status": "in_progress", "position": 0},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.column_ids("in_progress"), [todo_ids[0], doing_id])
        self.assertEqual(self.column_ids("todo"), [todo_ids[1], todo_ids[2]])
        positions = Task.objects.filter(status="todo").order_by("position")
        self.assertEqual([t.position for t in positions], [0, 1])

    def test_move_position_clamped_to_column_end(self):
        ids = [self.create_task(title=f"T{i}").data["id"] for i in range(2)]
        response = self.client.post(
            f"/api/tasks/{ids[0]}/move/", {"status": "todo", "position": 99}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.column_ids("todo"), [ids[1], ids[0]])

    def test_move_rejects_invalid_payload(self):
        task_id = self.create_task().data["id"]
        response = self.client.post(
            f"/api/tasks/{task_id}/move/", {"status": "nope", "position": -1}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    # --- isolation ---

    def test_other_users_tasks_are_invisible(self):
        theirs = Task.objects.create(user=self.other, title="Secret", due_date=DATE)
        self.assertEqual(self.client.get(f"/api/tasks/?date={DATE}").data, [])
        self.assertEqual(self.client.get(f"/api/tasks/{theirs.pk}/").status_code, 404)
        self.assertEqual(
            self.client.patch(
                f"/api/tasks/{theirs.pk}/", {"title": "Hacked"}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(self.client.delete(f"/api/tasks/{theirs.pk}/").status_code, 404)
        self.assertEqual(
            self.client.post(
                f"/api/tasks/{theirs.pk}/move/",
                {"status": "done", "position": 0},
                format="json",
            ).status_code,
            404,
        )
