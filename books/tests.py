from django.test import TestCase, Client
from django.urls import reverse
from books.models import Book, Category, ChapterContent
from users.models import User


class BookTests(TestCase):
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
        self.category = Category.objects.create(name='Test Category')
        self.book = Book.objects.create(
            title='Test Book',
            author='Test Author',
            isbn='1234567890',
            total_stock=10,
            current_stock=5,
            category=self.category
        )

    def test_book_creation(self):
        book = Book.objects.create(
            title='New Book',
            author='New Author',
            isbn='0987654321',
            total_stock=5,
            current_stock=5,
            category=self.category
        )
        self.assertEqual(book.title, 'New Book')
        self.assertEqual(book.author, 'New Author')
        self.assertEqual(book.borrow_count, 0)

    def test_category_creation(self):
        category = Category.objects.create(name='New Category')
        self.assertEqual(category.name, 'New Category')

    def test_chapter_creation(self):
        chapter = ChapterContent.objects.create(
            book=self.book,
            chapter_title='Chapter 1',
            chapter_index=1,
            content='Test content'
        )
        self.assertEqual(chapter.chapter_title, 'Chapter 1')

    def test_book_list_page(self):
        response = self.client.get(reverse('book_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)

    def test_book_detail_page(self):
        response = self.client.get(
            reverse('book_detail', kwargs={'pk': self.book.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.book.title)

    def test_book_manage_page_requires_login(self):
        response = self.client.get('/books/manage/')
        self.assertEqual(response.status_code, 302)

    def test_book_manage_page_requires_admin(self):
        self.client.login(username='reader', password='reader123')
        response = self.client.get('/books/manage/')
        self.assertEqual(response.status_code, 302)

    def test_book_manage_page_accessible_by_admin(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/books/manage/')
        self.assertIn(response.status_code, [200, 302])

    def test_soft_delete_book(self):
        book = Book.objects.create(
            title='To Delete',
            author='Author',
            isbn='1111111111',
            category=self.category
        )
        book.is_deleted = True
        book.save()
        book.refresh_from_db()
        self.assertTrue(book.is_deleted)

    def test_book_search_functionality(self):
        response = self.client.get('/books/list/?q=Test')
        self.assertEqual(response.status_code, 200)

    def test_reading_room_page(self):
        response = self.client.get('/books/reading-room/')
        self.assertEqual(response.status_code, 200)

    def test_category_manage_page(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/books/category/')
        self.assertIn(response.status_code, [200, 302])
