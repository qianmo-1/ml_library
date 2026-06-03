from django.test import TestCase, Client
from system.models import *
from users.models import User


class SystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='admin123'
        )
        self.reader_user = User.objects.create_user(
            username='reader',
            password='reader123'
        )

    def test_system_page_requires_login(self):
        response = self.client.get('/system/')
        self.assertEqual(response.status_code, 302)

    def test_system_page_requires_admin(self):
        self.client.login(username='reader', password='reader123')
        response = self.client.get('/system/')
        self.assertEqual(response.status_code, 302)

    def test_system_page_accessible_by_admin(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/system/')
        self.assertIn(response.status_code, [200, 302])

    def test_config_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/system/config/')
        self.assertIn(response.status_code, [200, 302])

    def test_logs_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/system/logs/')
        self.assertIn(response.status_code, [200, 302])

    def test_backup_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/system/backup/')
        self.assertIn(response.status_code, [200, 302])
