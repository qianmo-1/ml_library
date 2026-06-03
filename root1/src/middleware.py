from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.contrib import messages

PUBLIC_PATHS = ["/login/", "/register/", "/logout/", "/forgot-password/", "/reset-password/", "/"]

EXEMPT_PREFIXES = ["/admin/", "/static/", "/media/"]

PUBLIC_PREFIXES = [
    "/books/list/", "/books/detail/", "/books/chapter/",
    "/books/read/", "/books/reading-room/", "/books/",
]

STAFF_ROLES = ("admin", "owner")

ADMIN_PREFIXES = [
    "/books/manage/", "/books/add/", "/books/edit/", "/books/delete/",
    "/books/batch-delete/",
    "/books/category/", "/books/category/add/", "/books/category/edit/", "/books/category/delete/",
    "/borrow/manage/", "/borrow/confirm-return/",
    "/stats/", "/stats/dashboard/", "/stats/export/",
    "/system/", "/system/config/", "/system/logs/", "/system/backup/",
    "/users/manage/", "/users/edit/", "/users/freeze/", "/users/unfreeze/",
    "/users/reset-password/",
]


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        for prefix in EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        if path in PUBLIC_PATHS:
            return self.get_response(request)

        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        if not request.user.is_authenticated:
            try:
                resolve(path)
            except Resolver404:
                return self.get_response(request)
            messages.warning(request, "请先登录")
            return redirect(reverse("login"))

        if request.user.is_frozen and path != "/logout/" and path != "/login/":
            messages.error(request, "您的账号已被冻结，请联系管理员")
            return redirect(reverse("login"))

        for admin_path in ADMIN_PREFIXES:
            if path.startswith(admin_path):
                if request.user.role not in STAFF_ROLES:
                    messages.error(request, "无权访问管理页面")
                    return redirect(reverse("index"))
                break

        return self.get_response(request)