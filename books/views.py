from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.contrib.auth.decorators import login_required
from functools import wraps

from .models import Book, Category, ChapterContent
from borrow.models import OperationLog, BorrowRecord

import json
import unicodedata


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def _json_response(code, msg, data=None):
    payload = {"code": code, "msg": msg}
    if data is not None:
        payload["data"] = data
    return JsonResponse(payload, status=code)


def _admin_required(request, redirect_to="/"):
    if request.user.role not in ("admin", "owner"):
        messages.error(request, "您没有管理员权限")
        return redirect(redirect_to)
    return None


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ips = x_forwarded_for.split(",")
        for ip in ips:
            ip = ip.strip()
            if ip and not ip.startswith(("10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.", "192.168.", "127.", "0.")):
                return ip
        return ips[0].strip() if ips else request.META.get("REMOTE_ADDR", "")
    return request.META.get("REMOTE_ADDR", "")


def book_list_view(request):
    try:
        queryset = Book.objects.filter(is_deleted=False).select_related("category")

        q = request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(author__icontains=q) | Q(isbn__icontains=q)
            )

        category_id = request.GET.get("category", "").strip()
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        paginator = Paginator(queryset.order_by("-created_at"), 12)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        categories = Category.objects.all()

        context = {
            "books": page_obj,
            "categories": categories,
            "search_query": q,
            "category_id": category_id,
        }
        return render(request, "books/book_list.html", context)
    except Exception:
        messages.error(request, "获取图书列表失败，请稍后重试")
        return render(request, "books/book_list.html", {"books": [], "categories": []})


def reading_room_view(request):
    try:
        categories = Category.objects.all()
        category_id = request.GET.get("category", "").strip()
        q = request.GET.get("q", "").strip()

        queryset = Book.objects.filter(is_deleted=False).select_related("category")
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(author__icontains=q) | Q(isbn__icontains=q)
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        books_by_category = {}
        for cat in categories:
            cat_books = [b for b in queryset if b.category_id == cat.id]
            if cat_books:
                books_by_category[cat] = cat_books
            elif not category_id:
                pass

        uncategorized = [b for b in queryset if b.category_id is None]
        if uncategorized:
            books_by_category["未分类"] = uncategorized

        all_books = list(queryset.order_by("-borrow_count"))
        total_books = queryset.count()
        total_chapters = sum(
            ChapterContent.objects.filter(book__in=queryset, book__is_deleted=False).values("book").annotate(cnt=Count("id")).values_list("cnt", flat=True)
        )

        return render(request, "books/reading_room.html", {
            "categories": categories,
            "books_by_category": books_by_category,
            "all_books": all_books,
            "total_books": total_books,
            "category_id": category_id,
            "search_query": q,
            "popular_books": sorted(all_books, key=lambda b: b.borrow_count, reverse=True)[:6],
            "recent_books": list(queryset.order_by("-created_at")[:6]),
        })
    except Exception:
        messages.error(request, "加载阅览室失败，请稍后重试")
        return render(request, "books/reading_room.html", {
            "categories": [], "books_by_category": {}, "all_books": [],
            "total_books": 0, "category_id": "", "search_query": "",
            "popular_books": [], "recent_books": [],
        })


def book_detail_view(request, book_id):
    try:
        book = get_object_or_404(Book.objects.select_related("category"), id=book_id, is_deleted=False)

        user_borrow = None
        if request.user.is_authenticated:
            user_borrow = BorrowRecord.objects.filter(
                user=request.user, book=book, status__in=["borrowing", "overdue"]
            ).first()

        related_books = Book.objects.filter(
            is_deleted=False, category=book.category
        ).exclude(id=book.id).order_by("-borrow_count")[:4]

        toc_list = []
        if book.toc:
            try:
                toc_list = json.loads(book.toc)
            except (json.JSONDecodeError, TypeError):
                toc_list = []

        first_chapter = None
        chapter_count = 0
        try:
            chapters = ChapterContent.objects.filter(book=book).order_by("chapter_index")
            chapter_count = chapters.count()
            first_chapter = chapters.first()
        except Exception:
            pass

        return render(request, "books/book_detail.html", {
            "book": book,
            "user_borrow": user_borrow,
            "related_books": related_books,
            "toc_list": toc_list,
            "first_chapter": first_chapter,
            "chapter_count": chapter_count,
        })
    except Exception:
        messages.error(request, "获取图书详情失败，请稍后重试")
        return redirect("book_list")


def chapter_content_view(request, book_id, chapter_index):
    try:
        book = get_object_or_404(Book.objects.only("id", "title", "is_deleted"), id=book_id, is_deleted=False)

        chapter = get_object_or_404(
            ChapterContent.objects.only("chapter_title", "content"),
            book_id=book.id,
            chapter_index=chapter_index,
        )

        prev_chapter = ChapterContent.objects.filter(
            book_id=book.id, chapter_index__lt=chapter_index
        ).order_by("-chapter_index").only("chapter_index", "chapter_title").first()

        next_chapter = ChapterContent.objects.filter(
            book_id=book.id, chapter_index__gt=chapter_index
        ).order_by("chapter_index").only("chapter_index", "chapter_title").first()

        total_chapters = ChapterContent.objects.filter(book_id=book.id).count()

        return JsonResponse({
            "code": 200,
            "msg": "ok",
            "data": {
                "book_id": book.id,
                "book_title": book.title,
                "chapter_index": chapter_index,
                "chapter_title": chapter.chapter_title,
                "content": chapter.content,
                "prev": {"index": prev_chapter.chapter_index, "title": prev_chapter.chapter_title} if prev_chapter else None,
                "next": {"index": next_chapter.chapter_index, "title": next_chapter.chapter_title} if next_chapter else None,
                "total_chapters": total_chapters,
            },
        })
    except Exception:
        return JsonResponse({"code": 500, "msg": "获取章节内容失败，请稍后重试"})



def book_reader_view(request, book_id):
    try:
        book = get_object_or_404(Book.objects.select_related("category"), id=book_id, is_deleted=False)

        toc_list = []
        if book.toc:
            try:
                toc_list = json.loads(book.toc)
            except (json.JSONDecodeError, TypeError):
                toc_list = []

        chapters = ChapterContent.objects.filter(book=book).order_by("chapter_index")
        chapter_count = chapters.count()
        first_chapter = chapters.first()

        start_chapter = 0
        chapter_param = request.GET.get("chapter", "")
        if chapter_param:
            try:
                start_chapter = int(chapter_param)
            except ValueError:
                start_chapter = 0
        elif first_chapter:
            start_chapter = first_chapter.chapter_index

        if first_chapter:
            first_content = first_chapter.content
            first_title = first_chapter.chapter_title
        else:
            first_content = ""
            first_title = ""

        target_chapter = chapters.filter(chapter_index=start_chapter).first()
        if target_chapter:
            first_content = target_chapter.content
            first_title = target_chapter.chapter_title

        return render(request, "books/book_reader.html", {
            "book": book,
            "toc_list": toc_list,
            "chapter_count": chapter_count,
            "first_content": first_content,
            "first_title": first_title,
            "start_chapter": start_chapter,
        })
    except Exception:
        messages.error(request, "打开阅读器失败，请稍后重试")
        return redirect("book_list")


@login_required
def book_manage_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        queryset = Book.objects.filter(is_deleted=False).select_related("category")

        q = request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) | Q(author__icontains=q) | Q(isbn__icontains=q)
            )

        category_id = request.GET.get("category", "").strip()
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        paginator = Paginator(queryset.order_by("-created_at"), 12)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        for book in page_obj:
            book.active_borrow_count = book.borrowrecord_set.filter(
                status__in=["borrowing", "overdue"]
            ).count()

        categories = Category.objects.all()

        context = {
            "books": page_obj,
            "categories": categories,
            "q": q,
            "category": category_id,
        }
        return render(request, "books/book_manage.html", context)
    except Exception:
        messages.error(request, "获取图书管理列表失败，请稍后重试")
        return render(request, "books/book_manage.html", {"books": [], "categories": []})


@login_required
def book_add_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    if request.method == "POST":
        try:
            title = request.POST.get("title", "").strip()
            author = request.POST.get("author", "").strip()
            isbn = request.POST.get("isbn", "").strip()
            publisher = request.POST.get("publisher", "").strip()
            publish_date = request.POST.get("publish_date", "").strip() or None
            category_id = request.POST.get("category_id", "").strip()
            description = request.POST.get("description", "").strip()
            total_stock = request.POST.get("total_stock", "").strip()
            cover = request.FILES.get("cover")

            if not title or not author or not isbn:
                if _is_ajax(request):
                    return _json_response(400, "书名、作者、ISBN 为必填项")
                messages.error(request, "书名、作者、ISBN 为必填项")
                categories = Category.objects.all()
                return render(request, "books/book_add.html", {"categories": categories})

            if cover:
                ext = cover.name.rsplit(".", 1)[-1].lower() if "." in cover.name else ""
                if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
                    if _is_ajax(request):
                        return _json_response(400, "封面仅支持 JPG/PNG/GIF/WebP 格式")
                    messages.error(request, "封面仅支持 JPG/PNG/GIF/WebP 格式")
                    categories = Category.objects.all()
                    return render(request, "books/book_add.html", {"categories": categories})

            if Book.objects.filter(isbn=isbn, is_deleted=False).exists():
                if _is_ajax(request):
                    return _json_response(400, "该 ISBN 已存在")
                messages.error(request, "该 ISBN 已存在")
                categories = Category.objects.all()
                return render(request, "books/book_add.html", {"categories": categories})

            try:
                total_stock = int(total_stock) if total_stock else 0
            except (ValueError, TypeError):
                total_stock = 0

            category = None
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    pass

            book = Book.objects.create(
                title=title,
                author=author,
                isbn=isbn,
                publisher=publisher or None,
                publish_date=publish_date,
                category=category,
                description=description or None,
                cover=cover,
                total_stock=total_stock,
                current_stock=total_stock,
                borrow_count=0,
            )

            try:
                OperationLog.objects.create(
                    user=request.user,
                    action="create_book",
                    detail=f"新增图书《{book.title}》(ISBN: {book.isbn})，库存 {book.total_stock}",
                    ip_address=_get_client_ip(request),
                )
            except Exception:
                pass

            if _is_ajax(request):
                return _json_response(200, "添加成功", {"id": book.id})
            messages.success(request, f"图书《{book.title}》添加成功")
            return redirect("book_manage")
        except Exception:
            if _is_ajax(request):
                return _json_response(500, "添加失败，请稍后重试")
            messages.error(request, "添加失败，请稍后重试")
            categories = Category.objects.all()
            return render(request, "books/book_add.html", {"categories": categories})

    try:
        categories = Category.objects.all()
        return render(request, "books/book_add.html", {"categories": categories})
    except Exception:
        messages.error(request, "加载页面失败，请稍后重试")
        return render(request, "books/book_add.html", {"categories": []})


@login_required
def book_edit_view(request, book_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        book = get_object_or_404(Book, id=book_id, is_deleted=False)
    except Exception as e:
        if _is_ajax(request):
            return _json_response(404, "图书不存在")
        messages.error(request, "图书不存在")
        return redirect("book_manage")

    if request.method == "POST":
        try:
            title = request.POST.get("title", "").strip()
            author = request.POST.get("author", "").strip()
            isbn = request.POST.get("isbn", "").strip()
            publisher = request.POST.get("publisher", "").strip()
            publish_date = request.POST.get("publish_date", "").strip() or None
            category_id = request.POST.get("category_id", "").strip()
            description = request.POST.get("description", "").strip()
            new_total_stock = request.POST.get("total_stock", "").strip()
            cover = request.FILES.get("cover")

            if not title or not author or not isbn:
                if _is_ajax(request):
                    return _json_response(400, "书名、作者、ISBN 为必填项")
                messages.error(request, "书名、作者、ISBN 为必填项")
                categories = Category.objects.all()
                return render(request, "books/book_edit.html", {"book": book, "categories": categories})

            if Book.objects.filter(isbn=isbn, is_deleted=False).exclude(id=book.id).exists():
                if _is_ajax(request):
                    return _json_response(400, "该 ISBN 已被其他图书使用")
                messages.error(request, "该 ISBN 已被其他图书使用")
                categories = Category.objects.all()
                return render(request, "books/book_edit.html", {"book": book, "categories": categories})

            old_total = book.total_stock
            old_current = book.current_stock
            detail_parts = []

            if book.title != title:
                detail_parts.append(f"书名: {book.title} -> {title}")
            if book.author != author:
                detail_parts.append(f"作者: {book.author} -> {author}")
            if book.isbn != isbn:
                detail_parts.append(f"ISBN: {book.isbn} -> {isbn}")
            if book.publisher != publisher:
                detail_parts.append(f"出版社: {book.publisher or '无'} -> {publisher or '无'}")

            book.title = title
            book.author = author
            book.isbn = isbn
            book.publisher = publisher or None
            book.publish_date = publish_date if publish_date else None

            if category_id:
                try:
                    book.category = Category.objects.get(id=category_id)
                    detail_parts.append(f"分类已更新")
                except Category.DoesNotExist:
                    book.category = None
            else:
                book.category = None

            book.description = description if description else None

            try:
                new_total_stock = int(new_total_stock) if new_total_stock else old_total
            except (ValueError, TypeError):
                new_total_stock = old_total

            if new_total_stock != old_total:
                if old_total > 0:
                    new_current = max(0, int(old_current * new_total_stock / old_total))
                else:
                    new_current = new_total_stock
                detail_parts.append(f"总库存: {old_total} -> {new_total_stock}")
                detail_parts.append(f"当前库存: {old_current} -> {new_current}")
                book.total_stock = new_total_stock
                book.current_stock = new_current

            if cover:
                ext = cover.name.rsplit(".", 1)[-1].lower() if "." in cover.name else ""
                if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
                    if _is_ajax(request):
                        return _json_response(400, "封面仅支持 JPG/PNG/GIF/WebP 格式")
                    messages.error(request, "封面仅支持 JPG/PNG/GIF/WebP 格式")
                    categories = Category.objects.all()
                    return render(request, "books/book_edit.html", {"book": book, "categories": categories})
                book.cover = cover
                detail_parts.append("封面已更新")

            book.save()

            try:
                detail = "; ".join(detail_parts) if detail_parts else "无变更"
                OperationLog.objects.create(
                    user=request.user,
                    action="edit_book",
                    detail=f"编辑图书《{book.title}》(ID: {book.id}): {detail}",
                    ip_address=_get_client_ip(request),
                )
            except Exception:
                pass

            if _is_ajax(request):
                return _json_response(200, "修改成功", {"id": book.id})
            messages.success(request, f"图书《{book.title}》修改成功")
            return redirect("book_manage")
        except Exception:
            if _is_ajax(request):
                return _json_response(500, "修改失败，请稍后重试")
            messages.error(request, "修改失败，请稍后重试")
            categories = Category.objects.all()
            return render(request, "books/book_edit.html", {"book": book, "categories": categories})

    try:
        categories = Category.objects.all()
        return render(request, "books/book_edit.html", {"book": book, "categories": categories})
    except Exception:
        messages.error(request, "加载页面失败，请稍后重试")
        return render(request, "books/book_edit.html", {"book": book, "categories": []})


@login_required
def book_delete_view(request, book_id):
    admin_check = _admin_required(request)
    if admin_check:
        return _json_response(403, "您没有管理员权限")

    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        book = get_object_or_404(Book, id=book_id, is_deleted=False)
    except Exception:
        return _json_response(404, "图书不存在或已被删除")

    try:
        active_borrows = book.borrowrecord_set.filter(status__in=["borrowing", "overdue"]).count()
        if active_borrows > 0:
            return _json_response(400, f"该书有 {active_borrows} 条活跃借阅记录，无法删除")

        book.is_deleted = True
        book.save()

        try:
            OperationLog.objects.create(
                user=request.user,
                action="delete_book",
                detail=f"删除图书《{book.title}》(ID: {book.id}, ISBN: {book.isbn})",
                ip_address=_get_client_ip(request),
            )
        except Exception:
            pass

        return _json_response(200, "删除成功")
    except Exception:
        return _json_response(500, "删除失败，请稍后重试")


@login_required
def chapter_manage_view(request, book_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check
    try:
        book = get_object_or_404(Book, id=book_id, is_deleted=False)
        chapters = ChapterContent.objects.filter(book=book).order_by("chapter_index")
        return render(request, "books/book_chapters.html", {"book": book, "chapters": chapters})
    except Exception:
        messages.error(request, "加载章节管理页面失败，请稍后重试")
        return redirect("book_manage")


@login_required
def chapter_add_view(request, book_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check
    try:
        book = get_object_or_404(Book, id=book_id, is_deleted=False)
    except Exception:
        return _json_response(404, "图书不存在")

    if request.method != "POST":
        return _json_response(405, "仅支持POST请求")

    try:
        chapter_title = request.POST.get("chapter_title", "").strip()
        chapter_index = request.POST.get("chapter_index", "").strip()
        content = request.POST.get("content", "").strip()

        if not chapter_title:
            return _json_response(400, "请输入章节标题")
        if not chapter_index:
            return _json_response(400, "请输入章节序号")

        try:
            chapter_index = int(chapter_index)
        except (ValueError, TypeError):
            return _json_response(400, "章节序号必须为数字")

        if ChapterContent.objects.filter(book=book, chapter_index=chapter_index).exists():
            return _json_response(400, f"第 {chapter_index} 章已存在，请使用其他序号或编辑已有章节")

        chapter = ChapterContent.objects.create(
            book=book, chapter_index=chapter_index,
            chapter_title=chapter_title, content=content,
        )

        try:
            OperationLog.objects.create(
                user=request.user, action="create_chapter",
                detail=f"为《{book.title}》新增第{chapter_index}章「{chapter_title}」",
                ip_address=_get_client_ip(request),
            )
        except Exception:
            pass

        return _json_response(200, "章节添加成功", {"id": chapter.id, "chapter_index": chapter_index})
    except Exception:
        return _json_response(500, "添加失败，请稍后重试")


@login_required
def chapter_edit_view(request, book_id, chapter_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check
    try:
        chapter = get_object_or_404(ChapterContent, id=chapter_id, book_id=book_id)
    except Exception:
        return _json_response(404, "章节不存在")

    if request.method != "POST":
        return _json_response(405, "仅支持POST请求")

    try:
        chapter_title = request.POST.get("chapter_title", "").strip()
        content = request.POST.get("content", "").strip()

        if not chapter_title:
            return _json_response(400, "请输入章节标题")

        chapter.chapter_title = chapter_title
        chapter.content = content
        chapter.save()

        try:
            OperationLog.objects.create(
                user=request.user, action="edit_chapter",
                detail=f"编辑《{chapter.book.title}》第{chapter.chapter_index}章",
                ip_address=_get_client_ip(request),
            )
        except Exception:
            pass

        return _json_response(200, "章节更新成功")
    except Exception:
        return _json_response(500, "更新失败，请稍后重试")


@login_required
def chapter_delete_view(request, book_id, chapter_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check
    try:
        chapter = get_object_or_404(ChapterContent, id=chapter_id, book_id=book_id)
    except Exception:
        return _json_response(404, "章节不存在")

    try:
        book_title = chapter.book.title
        ch_index = chapter.chapter_index
        chapter.delete()

        try:
            OperationLog.objects.create(
                user=request.user, action="delete_chapter",
                detail=f"删除《{book_title}》第{ch_index}章",
                ip_address=_get_client_ip(request),
            )
        except Exception:
            pass

        return _json_response(200, "章节删除成功")
    except Exception:
        return _json_response(500, "删除失败，请稍后重试")


@login_required
def chapter_batch_view(request, book_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check
    try:
        book = get_object_or_404(Book, id=book_id, is_deleted=False)
    except Exception:
        return _json_response(404, "图书不存在")

    if request.method != "POST":
        return _json_response(405, "仅支持POST请求")

    try:
        body = json.loads(request.body)
        chapters_data = body.get("chapters", [])
        if not chapters_data:
            return _json_response(400, "请提供章节数据")

        created = 0
        for ch in chapters_data:
            idx = ch.get("chapter_index")
            title = ch.get("chapter_title", "").strip()
            content = ch.get("content", "")
            if not title or idx is None:
                continue
            try:
                idx = int(idx)
            except (ValueError, TypeError):
                continue
            obj, is_new = ChapterContent.objects.update_or_create(
                book=book, chapter_index=idx,
                defaults={"chapter_title": title, "content": content},
            )
            if is_new:
                created += 1

        return _json_response(200, f"成功更新 {len(chapters_data)} 章，新增 {created} 章",
                            {"created": created, "updated": len(chapters_data) - created})
    except Exception:
        return _json_response(500, "批量导入失败，请稍后重试")


@login_required
def book_batch_delete_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return _json_response(403, "您没有管理员权限")

    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        body = json.loads(request.body.decode("utf-8"))
        book_ids = body.get("ids", [])
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_response(400, "请求数据格式错误")

    if not book_ids or not isinstance(book_ids, list):
        return _json_response(400, "请提供要删除的图书 ID 列表")

    try:
        success_ids = []
        failed_items = []

        for book_id in book_ids:
            try:
                book = Book.objects.get(id=book_id, is_deleted=False)
            except Book.DoesNotExist:
                failed_items.append({"id": book_id, "reason": "图书不存在或已被删除"})
                continue

            active_borrows = book.borrowrecord_set.filter(status__in=["borrowing", "overdue"]).count()
            if active_borrows > 0:
                failed_items.append({"id": book_id, "title": book.title, "reason": f"有 {active_borrows} 条活跃借阅记录"})
                continue

            book.is_deleted = True
            book.save()
            success_ids.append(book_id)

            try:
                OperationLog.objects.create(
                    user=request.user,
                    action="delete_book",
                    detail=f"批量删除图书《{book.title}》(ID: {book.id}, ISBN: {book.isbn})",
                    ip_address=_get_client_ip(request),
                )
            except Exception:
                pass

        return _json_response(
            200,
            f"成功删除 {len(success_ids)} 本，失败 {len(failed_items)} 本",
            {"success": success_ids, "failed": failed_items},
        )
    except Exception:
        return _json_response(500, "批量删除失败，请稍后重试")


@login_required
def category_manage_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        categories = Category.objects.annotate(
            book_count=Count("book", filter=Q(book__is_deleted=False))
        ).order_by("-created_at")
        return render(request, "books/category_manage.html", {"categories": categories})
    except Exception:
        messages.error(request, "获取分类列表失败，请稍后重试")
        return render(request, "books/category_manage.html", {"categories": []})


@login_required
def category_add_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            if _is_ajax(request):
                return _json_response(400, "分类名称不能为空")
            messages.error(request, "分类名称不能为空")
            return redirect("category_manage")

        if Category.objects.filter(name=name).exists():
            if _is_ajax(request):
                return _json_response(400, "该分类名称已存在")
            messages.error(request, "该分类名称已存在")
            return redirect("category_manage")

        category = Category.objects.create(
            name=name,
            description=description or None,
        )

        try:
            OperationLog.objects.create(
                user=request.user,
                action="create_category",
                detail=f"新增分类「{category.name}」",
                ip_address=_get_client_ip(request),
            )
        except Exception:
            pass

        if _is_ajax(request):
            return _json_response(200, "添加成功", {"id": category.id, "name": category.name})
        messages.success(request, f"分类「{category.name}」添加成功")
        return redirect("category_manage")
    except Exception:
        if _is_ajax(request):
            return _json_response(500, "添加失败，请稍后重试")
        messages.error(request, "添加失败，请稍后重试")
        return redirect("category_manage")


@login_required
def category_edit_view(request, cat_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        category = get_object_or_404(Category, id=cat_id)
    except Exception:
        if _is_ajax(request):
            return _json_response(404, "分类不存在")
        messages.error(request, "分类不存在")
        return redirect("category_manage")

    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            if _is_ajax(request):
                return _json_response(400, "分类名称不能为空")
            messages.error(request, "分类名称不能为空")
            return redirect("category_manage")

        if Category.objects.filter(name=name).exclude(id=cat_id).exists():
            if _is_ajax(request):
                return _json_response(400, "该分类名称已存在")
            messages.error(request, "该分类名称已存在")
            return redirect("category_manage")

        old_name = category.name
        category.name = name
        category.description = description or None
        category.save()

        try:
            OperationLog.objects.create(
                user=request.user,
                action="edit_category",
                detail=f"编辑分类「{old_name}」->「{category.name}」",
                ip_address=_get_client_ip(request),
            )
        except Exception:
            pass

        if _is_ajax(request):
            return _json_response(200, "修改成功", {"id": category.id, "name": category.name})
        messages.success(request, f"分类「{category.name}」修改成功")
        return redirect("category_manage")
    except Exception:
        if _is_ajax(request):
            return _json_response(500, "修改失败，请稍后重试")
        messages.error(request, "修改失败，请稍后重试")
        return redirect("category_manage")


@login_required
def category_delete_view(request, cat_id):
    admin_check = _admin_required(request)
    if admin_check:
        return _json_response(403, "您没有管理员权限")

    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        category = get_object_or_404(Category, id=cat_id)
    except Exception:
        return _json_response(404, "分类不存在")

    try:
        book_count = Book.objects.filter(category=category, is_deleted=False).count()
        if book_count > 0:
            return _json_response(400, f"该分类下有 {book_count} 本图书，无法删除")

        category_name = category.name
        category.delete()

        try:
            OperationLog.objects.create(
                user=request.user,
                action="delete_category",
                detail=f"删除分类「{category_name}」",
                ip_address=_get_client_ip(request),
            )
        except Exception:
            pass

        return _json_response(200, "删除成功")
    except Exception:
        return _json_response(500, "删除失败，请稍后重试")