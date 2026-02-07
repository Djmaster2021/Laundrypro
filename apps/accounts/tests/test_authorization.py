from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client, TestCase

from apps.customers.models import Customer


class AuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")
        Customer.objects.create(first_name="Cliente", last_name="Demo", phone="5551112233")

    def setUp(self):
        self.client = Client()
        self.no_role_user = User.objects.create_user(username="norole", password="Pass12345!")
        self.seller_user = User.objects.create_user(username="seller", password="Pass12345!")
        self.manager_user = User.objects.create_user(username="manager", password="Pass12345!")

        self.seller_user.groups.add(Group.objects.get(name="Vendedora"))
        self.manager_user.groups.add(Group.objects.get(name="Encargada"))

    def test_customers_api_requires_authentication(self):
        response = self.client.get("/api/customers/")
        self.assertEqual(response.status_code, 403)

    def test_customers_api_blocks_authenticated_user_without_permissions(self):
        self.client.force_login(self.no_role_user)
        response = self.client.get("/api/customers/")
        self.assertEqual(response.status_code, 403)

    def test_customers_api_allows_user_with_role_permissions(self):
        self.client.force_login(self.seller_user)
        response = self.client.get("/api/customers/")
        self.assertEqual(response.status_code, 200)

    def test_reports_summary_api_blocks_seller_role(self):
        self.client.force_login(self.seller_user)
        response = self.client.get("/api/reports/summary/")
        self.assertEqual(response.status_code, 403)

    def test_reports_summary_api_allows_manager_role(self):
        self.client.force_login(self.manager_user)
        response = self.client.get("/api/reports/summary/")
        self.assertEqual(response.status_code, 200)

    def test_manager_dashboard_blocks_seller_role(self):
        self.client.force_login(self.seller_user)
        response = self.client.get("/manager/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
