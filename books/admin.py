from django.contrib import admin
from .models import Category, Book, ChapterContent


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "isbn", "category", "total_stock", "current_stock", "borrow_count"]
    list_filter = ["category", "is_deleted"]
    search_fields = ["title", "author", "isbn"]


@admin.register(ChapterContent)
class ChapterContentAdmin(admin.ModelAdmin):
    list_display = ["book", "chapter_title", "chapter_index"]
    list_filter = ["book"]
    search_fields = ["chapter_title"]