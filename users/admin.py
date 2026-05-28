from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "role", "phone", "student_id", "is_frozen", "borrow_count", "total_fine", "date_joined"]
    list_filter = ["role", "is_frozen"]
    search_fields = ["username", "phone", "student_id"]