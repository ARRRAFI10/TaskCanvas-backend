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
