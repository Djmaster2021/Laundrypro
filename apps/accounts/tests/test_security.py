from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    LOGIN_RATE_LIMIT_ENABLED=True,
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS=3,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS=300,
    LOGIN_RATE_LIMIT_LOCK_SECONDS=300,
)
class LoginSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.username = "security_user"
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.login_url = reverse("login")

    def tearDown(self):
        cache.clear()

    def test_sql_injection_payload_does_not_authenticate(self):
        response = self.client.post(
            self.login_url,
            {"username": "' OR 1=1 --", "password": "anything"},
            REMOTE_ADDR="10.10.10.10",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_csrf_protection_blocks_post_without_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            self.login_url,
            {"username": self.username, "password": self.password},
            REMOTE_ADDR="10.10.10.11",
        )
        self.assertEqual(response.status_code, 403)

    def test_login_rate_limit_blocks_after_multiple_failures(self):
        for _ in range(3):
            response = self.client.post(
                self.login_url,
                {"username": self.username, "password": "wrong-pass"},
                REMOTE_ADDR="10.10.10.12",
            )
            self.assertEqual(response.status_code, 200)

        blocked_response = self.client.post(
            self.login_url,
            {"username": self.username, "password": self.password},
            REMOTE_ADDR="10.10.10.12",
        )
        self.assertEqual(blocked_response.status_code, 429)
        self.assertIn("Retry-After", blocked_response.headers)
