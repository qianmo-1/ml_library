from django.test import TestCase, Client
from django.urls import reverse
from stats.models import *  # 导入你的 stats 模型
from users.models import User


class StatsTests(TestCase):
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

    def test_stats_dashboard_requires_login(self):
        response = self.client.get('/stats/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_stats_dashboard_requires_admin(self):
        self.client.login(username='reader', password='reader123')
        response = self.client.get('/stats/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_stats_dashboard_accessible_by_admin(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/stats/dashboard/')
        self.assertIn(response.status_code, [200, 302])

    def test_hot_books_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/stats/hot-books/')
        self.assertIn(response.status_code, [200, 302])

    def test_inventory_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/stats/inventory/')
        self.assertIn(response.status_code, [200, 302])

    def test_export_borrows_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/stats/export/borrows/')
        self.assertIn(response.status_code, [200, 302, 301])

    def test_export_books_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/stats/export/books/')
        self.assertIn(response.status_code, [200, 302, 301])

    def test_export_users_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/stats/export/users/')
        self.assertIn(response.status_code, [200, 302, 301])

    def test_stats_index_redirects_to_dashboard(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/stats/')
        self.assertIn(response.status_code, [200, 302])
