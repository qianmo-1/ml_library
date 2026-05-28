from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

PUBLIC_PATHS = ["/login/", "/register/", "/logout/", "/forgot-password/", "/reset-password/", "/"]
BOOK_PUBLIC_PATHS = ["/books/"]

EXEMPT_PREFIXES = ["/admin/", "/static/", "/media/"]


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        for prefix in EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        if request.path.startswith("/books/") and not request.user.is_authenticated:
            if request.path == "/books/" or request.path.startswith("/books/list/") or request.path.startswith("/books/detail/") or request.path.startswith("/books/chapter/") or request.path.startswith("/books/read/") or request.path.startswith("/books/reading-room/"):
                return self.get_response(request)

        if path in PUBLIC_PATHS or path.startswith("/books/list/") or path.startswith("/books/detail/") or path.startswith("/books/chapter/") or path.startswith("/books/read/") or path.startswith("/books/reading-room/"):
            return self.get_response(request)

        if not request.user.is_authenticated:
            messages.warning(request, "请先登录")
            return redirect(reverse("login"))

        if request.user.is_frozen and path != "/logout/" and path != "/login/":
            messages.error(request, "您的账号已被冻结，请联系管理员")
            return redirect(reverse("login"))

        admin_paths = [
            "/books/manage/", "/books/add/", "/books/edit/", "/books/delete/",
            "/books/category/", "/books/category/add/", "/books/category/edit/", "/books/category/delete/",
            "/borrow/manage/", "/borrow/confirm-return/",
            "/stats/", "/stats/dashboard/", "/stats/export/",
            "/system/", "/system/config/", "/system/logs/", "/system/backup/",
            "/users/manage/", "/users/edit/", "/users/freeze/", "/users/unfreeze/",
        ]
        for admin_path in admin_paths:
            if path.startswith(admin_path):
                if request.user.role != "admin":
                    messages.error(request, "无权访问管理页面")
                    return redirect(reverse("index"))
                break

        return self.get_response(request)