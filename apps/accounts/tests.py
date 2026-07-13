from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class AuthAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "demo@example.com", "s3cure-pass!", first_name="Demo", last_name="User"
        )

    def login(self, password="s3cure-pass!"):
        return self.client.post(
            "/api/auth/login/", {"email": "demo@example.com", "password": password}
        )

    def test_login_returns_tokens_and_user(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "demo@example.com")
        self.assertEqual(response.data["user"]["first_name"], "Demo")

    def test_login_wrong_password_rejected(self):
        response = self.login(password="wrong-password")
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.data)

    def test_me_requires_auth(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_me_returns_profile_with_bearer_token(self):
        access = self.login().data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "demo@example.com")

    def test_refresh_issues_new_access_token(self):
        refresh = self.login().data["refresh"]
        response = self.client.post("/api/auth/refresh/", {"refresh": refresh})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_refresh_rejects_garbage_token(self):
        response = self.client.post("/api/auth/refresh/", {"refresh": "not-a-token"})
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.data)


class RegisterAPITests(APITestCase):
    url = "/api/auth/register/"
    valid = {
        "email": "newcomer@example.com",
        "password": "Str0ng-Enough!",
        "first_name": "New",
        "last_name": "Comer",
    }

    def test_register_creates_user_and_returns_session(self):
        response = self.client.post(self.url, self.valid)
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "newcomer@example.com")
        self.assertEqual(response.data["user"]["first_name"], "New")
        self.assertNotIn("password", response.data)
        self.assertTrue(User.objects.filter(email="newcomer@example.com").exists())

    def test_returned_access_token_works_immediately(self):
        access = self.client.post(self.url, self.valid).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "newcomer@example.com")

    def test_registered_user_can_then_log_in(self):
        self.client.post(self.url, self.valid)
        response = self.client.post(
            "/api/auth/login/",
            {"email": self.valid["email"], "password": self.valid["password"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_duplicate_email_rejected(self):
        self.client.post(self.url, self.valid)
        response = self.client.post(self.url, self.valid)
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])

    def test_duplicate_email_is_case_insensitive(self):
        self.client.post(self.url, self.valid)
        response = self.client.post(self.url, {**self.valid, "email": "NewComer@Example.com"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])
        self.assertEqual(User.objects.filter(email__iexact=self.valid["email"]).count(), 1)

    def test_weak_password_rejected_with_field_error(self):
        response = self.client.post(self.url, {**self.valid, "password": "12345"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["errors"])
        self.assertFalse(User.objects.filter(email=self.valid["email"]).exists())

    def test_invalid_email_rejected(self):
        response = self.client.post(self.url, {**self.valid, "email": "not-an-email"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])

    def test_names_are_optional(self):
        response = self.client.post(
            self.url, {"email": "minimal@example.com", "password": "Str0ng-Enough!"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["first_name"], "")

    def test_password_is_hashed_not_stored_plaintext(self):
        self.client.post(self.url, self.valid)
        user = User.objects.get(email=self.valid["email"])
        self.assertNotEqual(user.password, self.valid["password"])
        self.assertTrue(user.check_password(self.valid["password"]))

    def test_register_does_not_require_authentication(self):
        # DEFAULT_PERMISSION_CLASSES is IsAuthenticated — signup must opt out.
        response = self.client.post(self.url, self.valid)
        self.assertNotEqual(response.status_code, 401)

    def test_new_user_starts_with_no_data_from_other_users(self):
        access = self.client.post(self.url, self.valid).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(self.client.get("/api/images/").data, [])
        self.assertEqual(self.client.get("/api/tasks/?date=2026-07-13").data, [])
