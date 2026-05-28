from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="分类名称")
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name="分类描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "categories"
        verbose_name = "图书分类"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="书名")
    author = models.CharField(max_length=100, verbose_name="作者")
    isbn = models.CharField(max_length=20, unique=True, verbose_name="ISBN")
    publisher = models.CharField(max_length=100, blank=True, null=True, verbose_name="出版社")
    publish_date = models.DateField(blank=True, null=True, verbose_name="出版日期")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="分类")
    description = models.TextField(blank=True, null=True, verbose_name="简介")
    toc = models.TextField(blank=True, null=True, verbose_name="目录JSON")
    cover = models.ImageField(upload_to="book_covers/", blank=True, null=True, verbose_name="封面")
    total_stock = models.IntegerField(default=0, verbose_name="总库存")
    current_stock = models.IntegerField(default=0, verbose_name="当前库存")
    borrow_count = models.IntegerField(default=0, verbose_name="累计借阅次数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="入库时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")

    class Meta:
        db_table = "books"
        verbose_name = "图书"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

    def is_available(self):
        return self.current_stock > 0 and not self.is_deleted


class ChapterContent(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="所属图书")
    chapter_index = models.IntegerField(verbose_name="章节序号")
    chapter_title = models.CharField(max_length=200, verbose_name="章节标题")
    content = models.TextField(blank=True, default="", verbose_name="章节内容")

    class Meta:
        db_table = "chapter_contents"
        verbose_name = "章节内容"
        verbose_name_plural = verbose_name
        ordering = ["book", "chapter_index"]
        unique_together = [("book", "chapter_index")]

    def __str__(self):
        return f"{self.book.title} - 第{self.chapter_index}章 {self.chapter_title}"