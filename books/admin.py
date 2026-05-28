from django.contrib import admin
from .models import Category, Book


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "isbn", "category", "total_stock", "current_stock", "borrow_count"]
    list_filter = ["category", "is_deleted"]
    search_fields = ["title", "author", "isbn"]