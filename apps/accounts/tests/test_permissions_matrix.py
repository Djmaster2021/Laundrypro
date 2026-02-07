from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client, TestCase

from apps.customers.models import Customer


class PermissionsMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")

    def setUp(self):
        self.client = Client()
        self.users = {
            "norole": User.objects.create_user(username="norole_matrix", password="Pass12345!"),
            "seller": User.objects.create_user(username="seller_matrix", password="Pass12345!"),
            "manager": User.objects.create_user(username="manager_matrix", password="Pass12345!"),
            "admin": User.objects.create_user(username="admin_matrix", password="Pass12345!"),
        }
        self.users["seller"].groups.add(Group.objects.get(name="Vendedora"))
        self.users["manager"].groups.add(Group.objects.get(name="Encargada"))
        self.users["admin"].groups.add(Group.objects.get(name="Administrador"))

    def _as_user(self, key):
        self.client.logout()
        self.client.force_login(self.users[key])

    def test_customers_read_matrix(self):
        Customer.objects.create(first_name="Demo", last_name="Read", phone="5550000001")
        expected = {"norole": 403, "seller": 200, "manager": 200, "admin": 200}

        for role, status_code in expected.items():
            with self.subTest(role=role):
                self._as_user(role)
                response = self.client.get("/api/customers/")
                self.assertEqual(response.status_code, status_code)

    def test_customers_create_matrix(self):
        expected = {"norole": 403, "seller": 201, "manager": 201, "admin": 201}

        for idx, (role, status_code) in enumerate(expected.items(), start=1):
            with self.subTest(role=role):
                self._as_user(role)
                payload = {
                    "first_name": f"Cliente{idx}",
                    "last_name": "Nuevo",
                    "phone": f"55500001{idx:02d}",
                }
                response = self.client.post("/api/customers/", payload)
                self.assertEqual(response.status_code, status_code)

    def test_services_create_matrix(self):
        expected = {"norole": 403, "seller": 403, "manager": 403, "admin": 201}

        for idx, (role, status_code) in enumerate(expected.items(), start=1):
            with self.subTest(role=role):
                self._as_user(role)
                payload = {
                    "code": f"TST-SVC-{idx}",
                    "name": f"Servicio test {idx}",
                    "description": "Servicio de validacion",
                    "category": "laundry",
                    "pricing_mode": "fijo",
                    "unit_price": "99.00",
                    "default_iva_rate": "16.00",
                    "is_active": True,
                }
                response = self.client.post("/api/catalog/services/", payload)
                self.assertEqual(response.status_code, status_code)

    def test_customers_delete_matrix(self):
        expected = {"norole": 403, "seller": 403, "manager": 403, "admin": 204}

        for idx, (role, status_code) in enumerate(expected.items(), start=1):
            with self.subTest(role=role):
                customer = Customer.objects.create(first_name=f"Delete{idx}", last_name="Case", phone=f"55500002{idx:02d}")
                self._as_user(role)
                response = self.client.delete(f"/api/customers/{customer.id}/")
                self.assertEqual(response.status_code, status_code)

    def test_reports_summary_matrix(self):
        expected = {"norole": 403, "seller": 403, "manager": 200, "admin": 200}

        for role, status_code in expected.items():
            with self.subTest(role=role):
                self._as_user(role)
                response = self.client.get("/api/reports/summary/")
                self.assertEqual(response.status_code, status_code)
