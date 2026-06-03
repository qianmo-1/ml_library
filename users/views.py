import json
from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required as django_login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from books.models import Book, Category
from borrow.models import BorrowRecord, FineRecord, OperationLog
from users.models import User


def custom_login_required(view_func):
    @wraps(view_func)
    @django_login_required(login_url=settings.LOGIN_URL)
    def wrapper(request, *args, **kwargs):
        if request.user.is_frozen:
            messages.error(request, "您的账号已被冻结，请联系管理员")
            if _is_ajax(request):
                return JsonResponse({"code": 403, "msg": "账号已被冻结", "data": None})
            logout(request)
            return redirect(settings.LOGIN_URL)
        return view_func(request, *args, **kwargs)

    return wrapper


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def _json_response(code=200, msg="ok", data=None):
    return JsonResponse({"code": code, "msg": msg, "data": data}, status=code)


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


def _rate_limited(key_prefix, limit=10, period=60):
    ip = key_prefix
    count = cache.get(ip, 0)
    if count >= limit:
        return True
    cache.set(ip, count + 1, period)
    return False


def register_view(request):
    if request.method == "GET":
        return render(request, "users/register.html")

    if not _is_ajax(request):
        return render(request, "users/register.html")

    client_ip = _get_client_ip(request)
    if _rate_limited(f"register_rate_{client_ip}", limit=5, period=300):
        return _json_response(429, "操作过于频繁，请5分钟后再试")

    try:
        body = json.loads(request.body) if request.body else request.POST.dict()
    except json.JSONDecodeError:
        body = request.POST.dict()

    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    phone = body.get("phone", "").strip() or None
    student_id = body.get("student_id", "").strip() or None
    email = body.get("email", "").strip() or ""

    if not username or not password:
        return _json_response(400, "用户名和密码不能为空")

    try:
        if User.objects.filter(username=username).exists():
            return _json_response(400, "用户名已存在")

        if phone and User.objects.filter(phone=phone).exists():
            return _json_response(400, "该手机号已被注册")

        if student_id and User.objects.filter(student_id=student_id).exists():
            return _json_response(400, "该学号/工号已被注册")

        try:
            validate_password(password)
        except ValidationError as ve:
            return _json_response(400, " ".join(ve.messages))

        user = User.objects.create(
            username=username,
            password=make_password(password),
            phone=phone,
            student_id=student_id,
            email=email,
        )
        return _json_response(200, "注册成功", {"user_id": user.id})
    except Exception as e:
        return _json_response(500, "注册失败，请稍后重试")


def login_view(request):
    if request.user.is_authenticated and not request.user.is_frozen:
        return redirect(reverse("index"))

    if request.method == "GET":
        return render(request, "users/login.html")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "").strip()

    if not username or not password:
        try:
            if request.body:
                try:
                    body = json.loads(request.body)
                    username = body.get("username", "").strip()
                    password = body.get("password", "").strip()
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

    if not username or not password:
        if _is_ajax(request):
            return _json_response(400, "用户名和密码不能为空")
        messages.error(request, "请输入用户名和密码")
        return render(request, "users/login.html")

    cache_key = f"login_brute_{username}"
    attempts = cache.get(cache_key, 0)
    if attempts >= 5:
        if _is_ajax(request):
            return JsonResponse({"code": 429, "msg": "登录尝试次数过多，请15分钟后再试", "data": None}, status=429)
        messages.error(request, "登录尝试次数过多，请15分钟后再试")
        return render(request, "users/login.html")

    try:
        user = authenticate(request, username=username, password=password)
        if user is None:
            cache.set(cache_key, attempts + 1, 900)
            if _is_ajax(request):
                return _json_response(400, "用户名或密码错误")
            messages.error(request, "用户名或密码错误，请重试")
            return render(request, "users/login.html")

        if user.is_frozen:
            if _is_ajax(request):
                return _json_response(403, "您的账号已被冻结，请联系管理员")
            messages.error(request, "您的账号已被冻结，请联系管理员")
            return render(request, "users/login.html")

        login(request, user)
        cache.delete(cache_key)

        OperationLog.objects.create(
            user=user,
            action="login",
            detail=f"用户 {user.username} 登录系统",
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        next_url = request.POST.get("next") or request.GET.get("next") or ""
        if next_url:
            parsed = urlparse(next_url)
            if parsed.scheme or parsed.netloc:
                next_url = ""
            elif not next_url.startswith("/"):
                next_url = ""
        if not next_url:
            next_url = reverse("index")
        if _is_ajax(request):
            return _json_response(200, "登录成功", {"next": next_url})
        return redirect(next_url)
    except Exception:
        if _is_ajax(request):
            return _json_response(500, "登录失败，请稍后重试")
        messages.error(request, "登录失败，请稍后重试")
        return render(request, "users/login.html")


def logout_view(request):
    if request.user.is_authenticated:
        try:
            OperationLog.objects.create(
                user=request.user,
                action="logout",
                detail=f"用户 {request.user.username} 退出登录",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            pass
    logout(request)
    messages.success(request, "您已成功退出登录")
    return redirect(reverse("login"))


def forgot_password_view(request):
    if request.method == "GET":
        return render(request, "users/forgot_password.html")

    if not _is_ajax(request):
        return render(request, "users/forgot_password.html")

    client_ip = _get_client_ip(request)
    if _rate_limited(f"forgot_pw_rate_{client_ip}", limit=5, period=300):
        return _json_response(429, "操作过于频繁，请5分钟后再试")

    try:
        body = json.loads(request.body) if request.body else request.POST.dict()
    except json.JSONDecodeError:
        body = request.POST.dict()

    username = body.get("username", "").strip()
    phone = body.get("phone", "").strip()
    student_id = body.get("student_id", "").strip()

    if not username:
        return _json_response(400, "请输入用户名")

    try:
        user = User.objects.filter(username=username).first()
        if user is None:
            return _json_response(400, "验证失败，请检查输入信息")

        has_phone = bool(user.phone)
        has_student_id = bool(user.student_id)

        if not has_phone and not has_student_id:
            return _json_response(400, "该账号未设置手机号或学号，无法自助找回密码，请联系管理员")

        if has_phone:
            if not phone:
                return _json_response(400, "验证失败，请检查输入信息")
            if user.phone != phone:
                return _json_response(400, "验证失败，请检查输入信息")

        if has_student_id:
            if not student_id:
                return _json_response(400, "验证失败，请检查输入信息")
            if user.student_id != student_id:
                return _json_response(400, "验证失败，请检查输入信息")

        request.session["reset_user_id"] = user.id
        request.session["reset_verified"] = True

        return _json_response(200, "验证通过", {"redirect": reverse("reset_password")})
    except Exception:
        return _json_response(500, "验证失败，请稍后重试")


def reset_password_view(request):
    if not request.session.get("reset_verified"):
        messages.warning(request, "请先完成身份验证")
        return redirect(reverse("forgot_password"))

    if request.method == "GET":
        return render(request, "users/reset_password.html")

    if not _is_ajax(request):
        return render(request, "users/reset_password.html")

    try:
        body = json.loads(request.body) if request.body else request.POST.dict()
    except json.JSONDecodeError:
        body = request.POST.dict()

    new_password = body.get("new_password", "").strip()
    confirm_password = body.get("confirm_password", "").strip()

    if not new_password or not confirm_password:
        return _json_response(400, "新密码不能为空")

    if new_password != confirm_password:
        return _json_response(400, "两次输入的密码不一致")

    try:
        user_id = request.session.get("reset_user_id")
        user = User.objects.get(id=user_id)
        user.password = make_password(new_password)
        user.save()

        request.session.pop("reset_user_id", None)
        request.session.pop("reset_verified", None)

        return _json_response(200, "密码重置成功，请重新登录", {"redirect": reverse("login")})
    except User.DoesNotExist:
        return _json_response(404, "用户不存在")
    except Exception:
        return _json_response(500, "密码重置失败，请稍后重试")


@custom_login_required
def profile_view(request):
    user = request.user

    if request.method == "GET":
        borrow_count = BorrowRecord.objects.filter(user=user, status="borrowing").count()
        user.borrow_count = borrow_count
        total_fine = FineRecord.objects.filter(user=user, is_paid=False).aggregate(t=Sum("fine_amount"))["t"] or 0
        user.total_fine = total_fine
        borrow_rules = {
            "MAX_BORROW_COUNT": getattr(settings, "MAX_BORROW_COUNT", 10),
            "BORROW_DAYS": getattr(settings, "BORROW_DAYS", 30),
            "FINE_PER_DAY": getattr(settings, "FINE_PER_DAY", 0.5),
        }
        return render(request, "users/profile.html", {
            "profile_user": user,
            "borrow_rules": borrow_rules,
        })

    if not _is_ajax(request):
        borrow_count = BorrowRecord.objects.filter(user=user, status="borrowing").count()
        user.borrow_count = borrow_count
        total_fine = FineRecord.objects.filter(user=user, is_paid=False).aggregate(t=Sum("fine_amount"))["t"] or 0
        user.total_fine = total_fine
        borrow_rules = {
            "MAX_BORROW_COUNT": getattr(settings, "MAX_BORROW_COUNT", 10),
            "BORROW_DAYS": getattr(settings, "BORROW_DAYS", 30),
            "FINE_PER_DAY": getattr(settings, "FINE_PER_DAY", 0.5),
        }
        return render(request, "users/profile.html", {
            "profile_user": user,
            "borrow_rules": borrow_rules,
        })

    try:
        body = json.loads(request.body) if request.body else request.POST.dict()
    except json.JSONDecodeError:
        body = request.POST.dict()

    action = body.get("action", "").strip()

    try:
        if action == "update_info":
            phone = body.get("phone", "").strip() or None
            email = body.get("email", "").strip() or ""

            if phone and phone != user.phone and User.objects.filter(phone=phone).exclude(id=user.id).exists():
                return _json_response(400, "该手机号已被其他用户使用")

            user.phone = phone
            user.email = email
            user.save()

            return _json_response(200, "个人信息更新成功", {
                "phone": user.phone,
                "email": user.email,
            })

        elif action == "change_password":
            old_password = body.get("old_password", "").strip()
            new_password = body.get("new_password", "").strip()
            confirm_password = body.get("confirm_password", "").strip()

            if not old_password or not new_password:
                return _json_response(400, "密码不能为空")

            if not user.check_password(old_password):
                return _json_response(400, "原密码错误")

            if new_password != confirm_password:
                return _json_response(400, "两次输入的新密码不一致")

            user.password = make_password(new_password)
            user.save()
            update_session_auth_hash(request, user)

            return _json_response(200, "密码修改成功")

        else:
            return _json_response(400, "无效的操作类型")

    except Exception:
        return _json_response(500, "操作失败，请稍后重试")


@custom_login_required
def my_borrows_view(request):
    user = request.user

    status_filter = request.GET.get("status", "").strip()
    page_number = request.GET.get("page", 1)

    try:
        queryset = BorrowRecord.objects.filter(user=user).select_related("book").order_by("-borrow_date")

        if status_filter and status_filter in ("borrowing", "returned", "overdue"):
            queryset = queryset.filter(status=status_filter)

        paginator = Paginator(queryset, 10)
        page_obj = paginator.get_page(page_number)

        borrowing_count = BorrowRecord.objects.filter(user=user, status="borrowing").count()

        context = {
            "borrows": page_obj,
            "current_status": status_filter,
            "borrowing_count": borrowing_count,
            "status_choices": BorrowRecord.STATUS_CHOICES,
        }

        if _is_ajax(request):
            data = {
                "borrows": [
                    {
                        "id": r.id,
                        "book_title": r.book.title,
                        "book_isbn": r.book.isbn,
                        "cover": r.book.cover.url if r.book.cover else None,
                        "borrow_date": r.borrow_date.strftime("%Y-%m-%d %H:%M"),
                        "due_date": r.due_date.strftime("%Y-%m-%d %H:%M"),
                        "return_date": r.return_date.strftime("%Y-%m-%d %H:%M") if r.return_date else None,
                        "status": r.status,
                        "status_display": r.get_status_display(),
                        "renew_count": r.renew_count,
                        "fine_amount": float(r.fine_amount),
                        "is_paid": r.is_paid,
                    }
                    for r in page_obj
                ],
                "has_previous": page_obj.has_previous(),
                "has_next": page_obj.has_next(),
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
            }
            return _json_response(200, "ok", data)

        return render(request, "users/my_borrows.html", context)
    except Exception:
        if _is_ajax(request):
            return _json_response(500, "查询失败，请稍后重试")
        messages.error(request, "查询借阅记录失败，请稍后重试")
        return render(request, "users/my_borrows.html", {"borrows": [], "status_filter": status_filter})


@custom_login_required
def my_fines_view(request):
    user = request.user

    status_filter = request.GET.get("status", "").strip()
    page_number = request.GET.get("page", 1)

    try:
        queryset = FineRecord.objects.filter(user=user).select_related(
            "borrow_record", "borrow_record__book"
        ).order_by("-created_at")

        if status_filter == "paid":
            queryset = queryset.filter(is_paid=True)
        elif status_filter == "unpaid":
            queryset = queryset.filter(is_paid=False)

        paginator = Paginator(queryset, 10)
        page_obj = paginator.get_page(page_number)

        total_unpaid = FineRecord.objects.filter(user=user, is_paid=False).aggregate(
            total=Sum("fine_amount")
        )["total"] or 0

        context = {
            "fines": page_obj,
            "current_status": status_filter,
            "total_unpaid": float(total_unpaid),
        }

        if _is_ajax(request):
            data = {
                "fines": [
                    {
                        "id": f.id,
                        "book_title": f.borrow_record.book.title,
                        "fine_amount": float(f.fine_amount),
                        "overdue_days": f.overdue_days,
                        "is_paid": f.is_paid,
                        "paid_at": f.paid_at.strftime("%Y-%m-%d %H:%M") if f.paid_at else None,
                        "created_at": f.created_at.strftime("%Y-%m-%d %H:%M"),
                    }
                    for f in page_obj
                ],
                "total_unpaid": float(total_unpaid),
                "has_previous": page_obj.has_previous(),
                "has_next": page_obj.has_next(),
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
            }
            return _json_response(200, "ok", data)

        return render(request, "users/my_fines.html", context)
    except Exception:
        if _is_ajax(request):
            return _json_response(500, "查询失败，请稍后重试")
        messages.error(request, "查询罚款记录失败，请稍后重试")
        return render(request, "users/my_fines.html", {"fines": [], "current_status": status_filter, "total_unpaid": 0})


def index_view(request):
    page_number = request.GET.get("page", 1)
    search_query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()

    try:
        books = Book.objects.filter(is_deleted=False).select_related("category")

        if search_query:
            books = books.filter(
                Q(title__icontains=search_query)
                | Q(author__icontains=search_query)
                | Q(isbn__icontains=search_query)
            )

        if category_id:
            books = books.filter(category_id=category_id)

        books = books.order_by("-created_at")

        paginator = Paginator(books, 12)
        page_obj = paginator.get_page(page_number)

        categories = Category.objects.annotate(book_count=Count("book", filter=Q(book__is_deleted=False))).order_by("name")

        total_books = Book.objects.filter(is_deleted=False).count()
        total_users = User.objects.count()

        hot_books = Book.objects.filter(is_deleted=False).select_related("category").order_by("-borrow_count")[:8]

        borrow_rules = getattr(settings, "SYSTEM_CONFIG", {
            "MAX_BORROW_COUNT": 10,
            "BORROW_DAYS": 30,
            "RENEW_TIMES": 1,
            "RENEW_DAYS": 30,
            "FINE_PER_DAY": 0.50,
        })

        context = {
            "books": page_obj,
            "categories": categories,
            "search_query": search_query,
            "category_id": category_id,
            "borrow_rules": borrow_rules,
            "total_books": total_books,
            "total_users": total_users,
            "hot_books": hot_books,
        }

        if request.user.is_authenticated and request.user.role in ("admin", "owner"):
            try:
                borrowing_count = BorrowRecord.objects.filter(status="borrowing").count()
                overdue_count = BorrowRecord.objects.filter(status="overdue").count()
                total_fine_unpaid = FineRecord.objects.filter(is_paid=False).aggregate(
                    total=Sum("fine_amount")
                )["total"] or 0

                context.update({
                    "is_admin": True,
                    "dashboard": {
                        "total_books": total_books,
                        "total_users": total_users,
                        "borrowing_count": borrowing_count,
                        "overdue_count": overdue_count,
                        "total_fine_unpaid": float(total_fine_unpaid),
                    },
                })
            except Exception:
                pass

        if _is_ajax(request):
            data = {
                "books": [
                    {
                        "id": b.id,
                        "title": b.title,
                        "author": b.author,
                        "isbn": b.isbn,
                        "publisher": b.publisher,
                        "category": b.category.name if b.category else None,
                        "cover": b.cover.url if b.cover else None,
                        "current_stock": b.current_stock,
                        "borrow_count": b.borrow_count,
                        "description": b.description,
                    }
                    for b in page_obj
                ],
                "categories": [
                    {"id": c.id, "name": c.name, "book_count": c.book_count}
                    for c in categories
                ],
                "has_previous": page_obj.has_previous(),
                "has_next": page_obj.has_next(),
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "borrow_rules": borrow_rules,
            }
            if context.get("is_admin"):
                data["dashboard"] = context["dashboard"]
            return _json_response(200, "ok", data)

        return render(request, "index.html", context)
    except Exception:
        if _is_ajax(request):
            return _json_response(500, "加载失败，请稍后重试")
        messages.error(request, "首页加载失败，请稍后重试")
        return render(request, "index.html", {
            "books": [],
            "categories": [],
            "search_query": search_query,
            "category_id": category_id,
            "borrow_rules": getattr(settings, "SYSTEM_CONFIG", {}),
        })


@custom_login_required
def manage_users_view(request):
    if request.user.role not in ("admin", "owner"):
        messages.error(request, "无权访问")
        return redirect(reverse("index"))

    page_number = request.GET.get("page", 1)
    search_query = request.GET.get("q", "").strip()

    try:
        queryset = User.objects.all().order_by("-date_joined")

        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query)
                | Q(phone__icontains=search_query)
                | Q(student_id__icontains=search_query)
            )

        paginator = Paginator(queryset, 15)
        page_obj = paginator.get_page(page_number)

        return render(request, "users/manage_users.html", {
            "users": page_obj,
            "search_query": search_query,
        })
    except Exception:
        messages.error(request, "查询失败，请稍后重试")
        return render(request, "users/manage_users.html", {"users": [], "search_query": search_query})


@custom_login_required
def edit_user_view(request, user_id):
    if request.user.role not in ("admin", "owner"):
        messages.error(request, "无权访问")
        return redirect(reverse("index"))

    target_user = get_object_or_404(User, id=user_id)

    if request.method == "GET":
        return render(request, "users/edit_user.html", {"target_user": target_user})

    if not _is_ajax(request):
        return render(request, "users/edit_user.html", {"target_user": target_user})

    try:
        body = json.loads(request.body) if request.body else request.POST.dict()
    except json.JSONDecodeError:
        body = request.POST.dict()

    try:
        email = body.get("email", "").strip()
        phone = body.get("phone", "").strip() or None
        role = body.get("role", "").strip()

        if phone and phone != target_user.phone and User.objects.filter(phone=phone).exclude(id=user_id).exists():
            return _json_response(400, "该手机号已被其他用户使用")

        if email:
            target_user.email = email
        if phone is not None:
            target_user.phone = phone
        if role:
            allowed_roles = ("reader", "admin", "owner")
            if role in allowed_roles:
                if role in ("admin", "owner") and request.user.role != "owner":
                    return _json_response(403, "仅拥有者可设置管理员或拥有者角色")
                if target_user.role == "owner" and request.user.role != "owner":
                    return _json_response(403, "仅拥有者可修改拥有者的信息")
                target_user.role = role

        target_user.save()

        try:
            OperationLog.objects.create(
                user=request.user,
                action="edit_user",
                detail=f"管理员编辑用户 {target_user.username} 信息",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            pass

        return _json_response(200, "用户信息更新成功")
    except Exception:
        return _json_response(500, "更新失败，请稍后重试")


@custom_login_required
def freeze_user_view(request, user_id):
    if request.user.role not in ("admin", "owner"):
        return _json_response(403, "无权操作")

    if request.method != "POST":
        return _json_response(405, "方法不允许")

    target_user = get_object_or_404(User, id=user_id)

    if target_user.id == request.user.id:
        return _json_response(400, "不能冻结自己的账号")

    if target_user.role == "owner" and request.user.role != "owner":
        return _json_response(403, "无权操作超级管理员")

    try:
        target_user.is_frozen = True
        target_user.save()

        try:
            OperationLog.objects.create(
                user=request.user,
                action="freeze_user",
                detail=f"管理员冻结用户 {target_user.username}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            pass

        messages.success(request, f"用户 {target_user.username} 已被冻结")
        return _json_response(200, "冻结成功")
    except Exception:
        return _json_response(500, "冻结失败，请稍后重试")


@custom_login_required
def unfreeze_user_view(request, user_id):
    if request.user.role not in ("admin", "owner"):
        return _json_response(403, "无权操作")

    if request.method != "POST":
        return _json_response(405, "方法不允许")

    target_user = get_object_or_404(User, id=user_id)

    if target_user.role == "owner" and request.user.role != "owner":
        return _json_response(403, "无权操作超级管理员")

    try:
        target_user.is_frozen = False
        target_user.save()

        try:
            OperationLog.objects.create(
                user=request.user,
                action="unfreeze_user",
                detail=f"管理员解封用户 {target_user.username}",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            pass

        messages.success(request, f"用户 {target_user.username} 已解封")
        return _json_response(200, "解封成功")
    except Exception:
        return _json_response(500, "解封失败，请稍后重试")


@custom_login_required
def admin_reset_password_view(request, user_id):
    if request.user.role not in ("admin", "owner"):
        return _json_response(403, "无权操作")

    if request.method != "POST":
        return _json_response(405, "方法不允许")

    target_user = get_object_or_404(User, id=user_id)

    if target_user.role == "owner" and request.user.role != "owner":
        return _json_response(403, "无权操作超级管理员")

    try:
        body = json.loads(request.body) if request.body else request.POST.dict()
    except json.JSONDecodeError:
        body = request.POST.dict()

    new_password = body.get("new_password", "").strip()

    if not new_password:
        return _json_response(400, "新密码不能为空")

    if len(new_password) < 6:
        return _json_response(400, "密码长度不能少于6位")

    try:
        target_user.password = make_password(new_password)
        target_user.save()

        try:
            OperationLog.objects.create(
                user=request.user,
                action="edit_user",
                detail=f"管理员重置用户 {target_user.username} 密码",
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            pass

        messages.success(request, f"已重置用户 {target_user.username} 的密码")
        return _json_response(200, "密码重置成功")
    except Exception:
        return _json_response(500, "密码重置失败，请稍后重试")