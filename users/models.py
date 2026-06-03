from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ("reader", "读者"),
        ("admin", "管理员"),
        ("owner", "拥有者"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="reader", verbose_name="角色")
    phone = models.CharField(max_length=11, unique=True, blank=True, null=True, verbose_name="手机号")
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="学号/工号")
    is_frozen = models.BooleanField(default=False, verbose_name="是否冻结")
    borrow_count = models.IntegerField(default=0, verbose_name="当前借阅数量")
    total_fine = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="累计罚款")

    class Meta:
        db_table = "users"
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username