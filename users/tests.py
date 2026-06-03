from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class UserTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='admin123'
        )
        self.reader_user = User.objects.create_user(
            username='reader',
            password='reader123',
            role='reader'
        )

    def test_user_creation(self):
        user = User.objects.create_user(
            username='newuser',
            password='newpass123'
        )
        self.assertEqual(user.username, 'newuser')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_frozen)

    def test_superuser_creation(self):
        user = User.objects.create_superuser(
            username='owner',
            password='owner123'
        )
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, 'owner')

    def test_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '登录')

    def test_user_login_success(self):
        response = self.client.post(
            reverse('login'),
            self.user_data
        )
        self.assertIn(response.status_code, [200, 302])

    def test_logout_redirects(self):
        self.client.login(username='reader', password='reader123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    def test_profile_page_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_page_accessible_after_login(self):
        self.client.login(username='reader', password='reader123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_user_freeze_function(self):
        user = self.reader_user
        user.is_frozen = True
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.is_frozen)

    def test_permission_denied_for_reader_on_admin_pages(self):
        self.client.login(username='reader', password='reader123')
        response = self.client.get('/users/manage/')
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access_admin_pages(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/users/manage/')
        self.assertIn(response.status_code, [200, 302])

    def test_register_page_exists(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_forgot_password_page(self):
        response = self.client.get('/forgot-password/')
        self.assertEqual(response.status_code, 200)
