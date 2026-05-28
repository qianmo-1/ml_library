from django.db import models
from django.conf import settings


class BorrowRecord(models.Model):
    STATUS_CHOICES = (
        ("borrowing", "借阅中"),
        ("returned", "已归还"),
        ("overdue", "已逾期"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="借阅用户")
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, verbose_name="图书")
    borrow_date = models.DateTimeField(auto_now_add=True, verbose_name="借阅日期")
    due_date = models.DateTimeField(verbose_name="应还日期")
    return_date = models.DateTimeField(blank=True, null=True, verbose_name="实际归还日期")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="borrowing", verbose_name="状态")
    renew_count = models.IntegerField(default=0, verbose_name="续借次数")
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="罚款金额")
    is_paid = models.BooleanField(default=False, verbose_name="罚款是否结清")

    class Meta:
        db_table = "borrow_records"
        verbose_name = "借阅记录"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


class OperationLog(models.Model):
    ACTION_CHOICES = (
        ("borrow", "借阅"),
        ("return", "归还"),
        ("renew", "续借"),
        ("create_book", "新增图书"),
        ("edit_book", "编辑图书"),
        ("delete_book", "删除图书"),
        ("create_user", "新增用户"),
        ("edit_user", "编辑用户"),
        ("freeze_user", "冻结用户"),
        ("unfreeze_user", "解封用户"),
        ("pay_fine", "缴纳罚款"),
        ("system_config", "系统设置"),
        ("data_backup", "数据备份"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="操作用户")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name="操作类型")
    detail = models.TextField(blank=True, null=True, verbose_name="操作详情")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP地址")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")

    class Meta:
        db_table = "operation_logs"
        verbose_name = "操作日志"
        verbose_name_plural = verbose_name


class SystemConfig(models.Model):
    key = models.CharField(max_length=50, unique=True, verbose_name="配置键")
    value = models.CharField(max_length=200, verbose_name="配置值")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="配置说明")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "system_configs"
        verbose_name = "系统配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.key}: {self.value}"


class FineRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="用户")
    borrow_record = models.ForeignKey(BorrowRecord, on_delete=models.CASCADE, verbose_name="关联借阅记录")
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="罚款金额")
    overdue_days = models.IntegerField(default=0, verbose_name="逾期天数")
    is_paid = models.BooleanField(default=False, verbose_name="是否结清")
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name="结清时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="生成时间")

    class Meta:
        db_table = "fine_records"
        verbose_name = "罚款记录"
        verbose_name_plural = verbose_name