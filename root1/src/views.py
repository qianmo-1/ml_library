from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from borrow.models import SystemConfig, OperationLog
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.conf import settings
import os
import datetime
import subprocess
import json
import sys


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def _json_response(code, msg, data=None):
    payload = {"code": code, "msg": msg}
    if data is not None:
        payload["data"] = data
    return JsonResponse(payload, status=code)


def _admin_required(request):
    if request.user.role not in ("admin", "owner"):
        if _is_ajax(request):
            return _json_response(403, "您没有管理员权限")
        messages.error(request, "您没有管理员权限")
        return redirect("/")
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


def _write_operation_log(request, action, detail):
    try:
        ip_address = _get_client_ip(request)
        OperationLog.objects.create(
            user=request.user,
            action=action,
            detail=detail,
            ip_address=ip_address,
        )
    except Exception:
        pass


SYSTEM_CONFIG_DEFAULTS = getattr(settings, "SYSTEM_CONFIG", {
    "MAX_BORROW_COUNT": 10,
    "BORROW_DAYS": 30,
    "RENEW_TIMES": 1,
    "RENEW_DAYS": 30,
    "FINE_PER_DAY": 0.50,
})

SYSTEM_CONFIG_DESCRIPTIONS = {
    "MAX_BORROW_COUNT": "最大借阅数量",
    "BORROW_DAYS": "借阅天数",
    "RENEW_TIMES": "最大续借次数",
    "RENEW_DAYS": "续借天数",
    "FINE_PER_DAY": "每日罚款金额（元）",
}

CONFIG_KEY_MAP = {
    "max_borrow_count": "MAX_BORROW_COUNT",
    "borrow_days": "BORROW_DAYS",
    "renew_times": "RENEW_TIMES",
    "renew_days": "RENEW_DAYS",
    "fine_per_day": "FINE_PER_DAY",
}


@login_required
def system_config_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        for key, default_value in SYSTEM_CONFIG_DEFAULTS.items():
            try:
                config = SystemConfig.objects.get(key=key)
            except SystemConfig.DoesNotExist:
                SystemConfig.objects.create(
                    key=key,
                    value=str(default_value),
                    description=SYSTEM_CONFIG_DESCRIPTIONS.get(key, ""),
                )

        configs = SystemConfig.objects.all().order_by("key")

        if request.method == "POST":
            update_details = []
            for form_key, config_key in CONFIG_KEY_MAP.items():
                new_value = request.POST.get(form_key, "").strip()
                if new_value == "" or new_value is None:
                    continue
                try:
                    config = SystemConfig.objects.get(key=config_key)
                    old_value = config.value
                    if old_value != new_value:
                        config.value = new_value
                        config.save()
                        update_details.append(f"{SYSTEM_CONFIG_DESCRIPTIONS.get(config_key, config_key)}: {old_value} -> {new_value}")
                except SystemConfig.DoesNotExist:
                    config = SystemConfig.objects.create(
                        key=config_key,
                        value=new_value,
                        description=SYSTEM_CONFIG_DESCRIPTIONS.get(config_key, ""),
                    )
                    update_details.append(f"新建 {SYSTEM_CONFIG_DESCRIPTIONS.get(config_key, config_key)}: {new_value}")

            if update_details:
                detail_text = "更新系统配置: " + "; ".join(update_details)
                _write_operation_log(request, "system_config", detail_text)

            configs = SystemConfig.objects.all().order_by("key")

            if _is_ajax(request):
                config_data = {c.key: c.value for c in configs}
                return _json_response(200, "系统配置已更新", {"configs": config_data})

            messages.success(request, "系统配置已更新")
            return redirect("system_config")

        config_dict = {}
        for c in configs:
            config_dict[c.key] = {"value": c.value, "description": c.description, "updated_at": c.updated_at}

        context = {"configs": config_dict, "config_meta": SYSTEM_CONFIG_DEFAULTS}
        return render(request, "system/config.html", context)

    except Exception:
        if _is_ajax(request):
            return _json_response(500, "系统配置操作失败，请稍后重试")
        messages.error(request, "系统配置操作失败，请稍后重试")
        return render(request, "system/config.html", {"configs": {}, "config_meta": {}})


@login_required
def system_logs_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        queryset = OperationLog.objects.select_related("user").all()

        action_filter = request.GET.get("action", "").strip()
        if action_filter:
            queryset = queryset.filter(action=action_filter)

        user_search = request.GET.get("user", "").strip()
        if user_search:
            queryset = queryset.filter(user__username__icontains=user_search)

        start_date = request.GET.get("start_date", "").strip()
        end_date = request.GET.get("end_date", "").strip()
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date + " 23:59:59")

        queryset = queryset.order_by("-created_at")

        paginator = Paginator(queryset, 20)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        action_choices = OperationLog.ACTION_CHOICES

        context = {
            "logs": page_obj,
            "action_filter": action_filter,
            "user_search": user_search,
            "start_date": start_date,
            "end_date": end_date,
            "action_choices": action_choices,
        }
        return render(request, "system/logs.html", context)

    except Exception as e:
        messages.error(request, "加载操作日志失败，请稍后重试")
        return render(request, "system/logs.html", {
            "logs": [],
            "action_filter": "",
            "user_search": "",
            "start_date": "",
            "end_date": "",
            "action_choices": [],
        })


def _get_backup_dir():
    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    return backup_dir


@login_required
def system_backup_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        backup_dir = _get_backup_dir()

        if request.method == "POST":
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backup_{timestamp}.json"
            backup_path = os.path.join(backup_dir, filename)

            manage_py = os.path.join(settings.BASE_DIR, "manage.py")
            result = subprocess.run(
                [sys.executable, manage_py, "dumpdata", "--exclude", "contenttypes", "--exclude", "sessions", "-o", backup_path],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                error_msg = result.stderr or "备份命令执行失败"
                if _is_ajax(request):
                    return _json_response(500, f"数据库备份失败: {error_msg}")
                messages.error(request, f"数据库备份失败: {error_msg}")
                return redirect("system_backup")

            _write_operation_log(request, "data_backup", f"创建数据库备份: {filename}")

            if _is_ajax(request):
                return _json_response(200, "数据库备份成功", {"filename": filename})

            messages.success(request, f"数据库备份成功: {filename}")
            return redirect("system_backup")

        backup_files = []
        if os.path.exists(backup_dir):
            for f in sorted(os.listdir(backup_dir), reverse=True):
                if f.endswith(".json"):
                    file_path = os.path.join(backup_dir, f)
                    file_size = os.path.getsize(file_path)
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    backup_files.append({
                        "filename": f,
                        "size": file_size,
                        "size_display": _format_file_size(file_size),
                        "modified": file_mtime.strftime("%Y-%m-%d %H:%M:%S"),
                    })

        context = {"backup_files": backup_files}
        return render(request, "system/backup.html", context)

    except Exception:
        if _is_ajax(request):
            return _json_response(500, "备份操作失败，请稍后重试")
        messages.error(request, "备份操作失败，请稍后重试")
        return render(request, "system/backup.html", {"backup_files": []})


def _format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _safe_backup_path(backup_dir, filename):
    safe_name = os.path.basename(filename)
    if safe_name != filename or safe_name.startswith("."):
        raise ValueError("非法文件名")
    if not safe_name.endswith(".json"):
        raise ValueError("非法的文件类型")
    full_path = os.path.normpath(os.path.join(backup_dir, safe_name))
    real_backup = os.path.realpath(backup_dir)
    real_path = os.path.realpath(full_path)
    if not real_path.startswith(real_backup + os.sep):
        raise ValueError("路径遍历检测")
    return real_path


@login_required
def download_backup_view(request, filename):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        backup_dir = _get_backup_dir()
        file_path = _safe_backup_path(backup_dir, filename)

        if not os.path.exists(file_path):
            messages.error(request, "备份文件不存在")
            return redirect("system_backup")

        with open(file_path, "rb") as f:
            file_content = f.read()

        response = HttpResponse(file_content, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{os.path.basename(filename)}"'
        response["Content-Length"] = len(file_content)
        return response

    except ValueError as e:
        messages.error(request, "非法的文件名")
        return redirect("system_backup")
    except Exception as e:
        messages.error(request, "下载备份文件失败，请稍后重试")
        return redirect("system_backup")


@login_required
def delete_backup_view(request, filename):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    if request.method != "POST":
        if _is_ajax(request):
            return _json_response(405, "请求方法不允许")
        messages.error(request, "请求方法不允许")
        return redirect("system_backup")

    try:
        backup_dir = _get_backup_dir()
        file_path = _safe_backup_path(backup_dir, filename)

        if not os.path.exists(file_path):
            if _is_ajax(request):
                return _json_response(404, "备份文件不存在")
            messages.error(request, "备份文件不存在")
            return redirect("system_backup")

        os.remove(file_path)

        _write_operation_log(request, "data_backup", f"删除数据库备份: {os.path.basename(filename)}")

        if _is_ajax(request):
            return _json_response(200, "备份文件已删除")

        messages.success(request, "备份文件已删除")
        return redirect("system_backup")

    except ValueError as e:
        if _is_ajax(request):
            return _json_response(400, "非法的文件名")
        messages.error(request, "非法的文件名")
        return redirect("system_backup")
    except Exception as e:
        if _is_ajax(request):
            return _json_response(500, "删除备份文件失败，请稍后重试")
        messages.error(request, "删除备份文件失败，请稍后重试")
        return redirect("system_backup")