from django.contrib import admin
from .models import BorrowRecord, OperationLog, SystemConfig, FineRecord


@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "borrow_date", "due_date", "return_date", "status", "fine_amount"]
    list_filter = ["status"]
    search_fields = ["user__username", "book__title"]


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "detail", "ip_address", "created_at"]
    list_filter = ["action"]
    search_fields = ["user__username"]


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "description", "updated_at"]


@admin.register(FineRecord)
class FineRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "borrow_record", "fine_amount", "overdue_days", "is_paid", "created_at"]
    list_filter = ["is_paid"]
    search_fields = ["user__username"]