from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Sum
from django.db import transaction
from django.contrib.auth.decorators import login_required

from .models import BorrowRecord, OperationLog, SystemConfig, FineRecord
from books.models import Book
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


def _json_response(code, msg, data=None):
    payload = {"code": code, "msg": msg}
    if data is not None:
        payload["data"] = data
    return JsonResponse(payload)


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _get_system_config():
    try:
        configs = SystemConfig.objects.all()
        result = {}
        for c in configs:
            result[c.key] = c.value
        return result
    except Exception:
        return {}



def _get_config_value(key, default):
    config = _get_system_config()
    val = config.get(key)
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            try:
                return float(val)
            except (ValueError, TypeError):
                return val
    fallback = getattr(settings, "SYSTEM_CONFIG", {})
    return fallback.get(key, default)


def _admin_required(request):
    if request.user.role != "admin":
        if _is_ajax(request):
            return _json_response(403, "您没有管理员权限")
        messages.error(request, "您没有管理员权限")
        return redirect("/")
    return None


@login_required
def borrow_book_view(request, book_id):
    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        user = request.user

        max_borrow_count = _get_config_value("MAX_BORROW_COUNT", 10)

        if user.is_frozen:
            return _json_response(400, "您的账户已被冻结，无法借阅图书")

        if user.borrow_count >= max_borrow_count:
            return _json_response(400, f"您当前借阅数量已达上限（{max_borrow_count}本），无法继续借阅")

        try:
            book = Book.objects.get(id=book_id, is_deleted=False)
        except Book.DoesNotExist:
            return _json_response(404, "图书不存在或已被删除")

        if book.current_stock <= 0:
            return _json_response(400, "该图书当前库存不足，无法借阅")

        borrow_days = _get_config_value("BORROW_DAYS", 30)

        with transaction.atomic():
            book = Book.objects.select_for_update().get(id=book_id, is_deleted=False)
            if book.current_stock <= 0:
                return _json_response(400, "该图书当前库存不足，无法借阅")

            user = User.objects.select_for_update().get(id=request.user.id)
            if user.borrow_count >= max_borrow_count:
                return _json_response(400, f"您当前借阅数量已达上限（{max_borrow_count}本），无法继续借阅")
            if user.is_frozen:
                return _json_response(400, "您的账户已被冻结，无法借阅图书")

            record = BorrowRecord.objects.create(
                user=user,
                book=book,
                borrow_date=timezone.now(),
                due_date=timezone.now() + timedelta(days=borrow_days),
                status="borrowing",
                renew_count=0,
            )

            book.current_stock -= 1
            book.save(update_fields=["current_stock"])

            user.borrow_count += 1
            user.save(update_fields=["borrow_count"])

            try:
                OperationLog.objects.create(
                    user=user,
                    action="borrow",
                    detail=f"借阅《{book.title}》，应还日期 {record.due_date.strftime('%Y-%m-%d')}",
                    ip_address=_get_client_ip(request),
                )
            except Exception:
                pass

        return _json_response(200, "借阅成功", {
            "record_id": record.id,
            "due_date": record.due_date.strftime("%Y-%m-%d %H:%M"),
            "book_title": book.title,
        })

    except Exception as e:
        return _json_response(500, f"借阅失败: {str(e)}")


@login_required
def renew_book_view(request, record_id):
    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        user = request.user

        try:
            record = BorrowRecord.objects.select_related("book").get(id=record_id)
        except BorrowRecord.DoesNotExist:
            return _json_response(404, "借阅记录不存在")

        if record.user_id != user.id:
            return _json_response(403, "您只能续借自己的借阅记录")

        if record.status != "borrowing":
            return _json_response(400, "该记录状态不允许续借")

        max_renew_count = _get_config_value("RENEW_TIMES", 1)
        if record.renew_count >= max_renew_count:
            return _json_response(400, f"续借次数已达上限（{max_renew_count}次），无法继续续借")

        if user.is_frozen:
            return _json_response(400, "您的账户已被冻结，无法续借")

        renew_days = _get_config_value("RENEW_DAYS", 30)

        with transaction.atomic():
            record = BorrowRecord.objects.select_for_update().get(id=record_id)
            if record.status != "borrowing":
                return _json_response(400, "该记录状态不允许续借")
            if record.renew_count >= max_renew_count:
                return _json_response(400, f"续借次数已达上限（{max_renew_count}次），无法继续续借")

            record.renew_count += 1
            record.due_date = record.due_date + timedelta(days=renew_days)
            record.save(update_fields=["renew_count", "due_date"])

            try:
                OperationLog.objects.create(
                    user=user,
                    action="renew",
                    detail=f"续借《{record.book.title}》第 {record.renew_count} 次，新应还日期 {record.due_date.strftime('%Y-%m-%d')}",
                    ip_address=_get_client_ip(request),
                )
            except Exception:
                pass

        return _json_response(200, "续借成功", {
            "record_id": record.id,
            "due_date": record.due_date.strftime("%Y-%m-%d %H:%M"),
            "renew_count": record.renew_count,
        })

    except Exception as e:
        return _json_response(500, f"续借失败: {str(e)}")


@login_required
def return_book_view(request, record_id):
    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        user = request.user

        try:
            record = BorrowRecord.objects.select_related("book").get(id=record_id)
        except BorrowRecord.DoesNotExist:
            return _json_response(404, "借阅记录不存在")

        if record.user_id != user.id:
            return _json_response(403, "您只能归还自己的借阅记录")

        if record.status not in ("borrowing", "overdue"):
            return _json_response(400, "该记录状态不允许归还")

        return_date = timezone.now()
        is_overdue = record.status == "overdue" or (record.status == "borrowing" and return_date > record.due_date)
        fine_amount = 0
        overdue_days = 0

        if is_overdue:
            effective_due = record.due_date
            delta = return_date - effective_due
            overdue_days = delta.days + (1 if delta.seconds > 0 else 0)
            if overdue_days <= 0:
                overdue_days = 1
            fine_per_day = _get_config_value("FINE_PER_DAY", 0.50)
            fine_amount = overdue_days * fine_per_day

        with transaction.atomic():
            record = BorrowRecord.objects.select_for_update().get(id=record_id)
            if record.status not in ("borrowing", "overdue"):
                return _json_response(400, "该记录状态不允许归还")

            book = Book.objects.select_for_update().get(id=record.book_id)

            record.status = "returned"
            record.return_date = return_date
            if fine_amount > 0:
                record.fine_amount = fine_amount
            record.save(update_fields=["status", "return_date", "fine_amount"])

            book.current_stock += 1
            book.save(update_fields=["current_stock"])

            update_user = User.objects.select_for_update().get(id=record.user_id)
            update_user.borrow_count = max(0, update_user.borrow_count - 1)
            if fine_amount > 0:
                update_user.total_fine += fine_amount
            update_user.save(update_fields=["borrow_count", "total_fine"])

            if fine_amount > 0:
                FineRecord.objects.create(
                    user=update_user,
                    borrow_record=record,
                    fine_amount=fine_amount,
                    overdue_days=overdue_days,
                    is_paid=False,
                )

            try:
                detail = f"归还《{record.book.title}》"
                if overdue_days > 0:
                    detail += f"，逾期 {overdue_days} 天，罚款 {fine_amount} 元"
                OperationLog.objects.create(
                    user=user,
                    action="return",
                    detail=detail,
                    ip_address=_get_client_ip(request),
                )
            except Exception:
                pass

        result_data = {
            "record_id": record.id,
            "return_date": return_date.strftime("%Y-%m-%d %H:%M"),
        }
        if overdue_days > 0:
            result_data["overdue_days"] = overdue_days
            result_data["fine_amount"] = float(fine_amount)

        return _json_response(200, "归还成功", result_data)

    except Exception as e:
        return _json_response(500, f"归还失败: {str(e)}")


@login_required
def borrow_manage_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        queryset = BorrowRecord.objects.select_related("user", "book").all()

        q = request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(user__username__icontains=q) | Q(book__title__icontains=q)
            )

        status_filter = request.GET.get("status", "").strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = Paginator(queryset.order_by("-borrow_date"), 15)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        now = timezone.now()
        for record in page_obj:
            record.is_overdue_display = record.status == "overdue" or (
                record.status == "borrowing" and record.due_date < now
            )

        context = {
            "records": page_obj,
            "q": q,
            "status_filter": status_filter,
            "now": now,
        }
        return render(request, "borrow/borrow_manage.html", context)

    except Exception as e:
        messages.error(request, f"获取借阅记录失败: {str(e)}")
        return render(request, "borrow/borrow_manage.html", {"records": [], "now": timezone.now()})


@login_required
def confirm_return_view(request, record_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        try:
            record = BorrowRecord.objects.select_related("book").get(id=record_id)
        except BorrowRecord.DoesNotExist:
            if _is_ajax(request):
                return _json_response(404, "借阅记录不存在")
            messages.error(request, "借阅记录不存在")
            return redirect("borrow_manage")

        if record.status not in ("borrowing", "overdue"):
            if _is_ajax(request):
                return _json_response(400, "该记录状态不允许归还")
            messages.error(request, "该记录状态不允许归还")
            return redirect("borrow_manage")

        return_date = timezone.now()
        is_overdue = record.status == "overdue" or (record.status == "borrowing" and return_date > record.due_date)
        fine_amount = 0
        overdue_days = 0

        if is_overdue:
            effective_due = record.due_date
            delta = return_date - effective_due
            overdue_days = delta.days + (1 if delta.seconds > 0 else 0)
            if overdue_days <= 0:
                overdue_days = 1
            fine_per_day = _get_config_value("FINE_PER_DAY", 0.50)
            fine_amount = overdue_days * fine_per_day

        with transaction.atomic():
            record = BorrowRecord.objects.select_for_update().get(id=record_id)
            if record.status not in ("borrowing", "overdue"):
                if _is_ajax(request):
                    return _json_response(400, "该记录状态不允许归还")
                messages.error(request, "该记录状态不允许归还")
                return redirect("borrow_manage")

            book = Book.objects.select_for_update().get(id=record.book_id)

            record.status = "returned"
            record.return_date = return_date
            if fine_amount > 0:
                record.fine_amount = fine_amount
            record.save(update_fields=["status", "return_date", "fine_amount"])

            book.current_stock += 1
            book.save(update_fields=["current_stock"])

            update_user = User.objects.select_for_update().get(id=record.user_id)
            update_user.borrow_count = max(0, update_user.borrow_count - 1)
            if fine_amount > 0:
                update_user.total_fine += fine_amount
            update_user.save(update_fields=["borrow_count", "total_fine"])

            if fine_amount > 0:
                FineRecord.objects.create(
                    user=update_user,
                    borrow_record=record,
                    fine_amount=fine_amount,
                    overdue_days=overdue_days,
                    is_paid=False,
                )

            try:
                detail = f"管理员确认归还《{record.book.title}》，借阅人: {record.user.username}"
                if overdue_days > 0:
                    detail += f"，逾期 {overdue_days} 天，罚款 {fine_amount} 元"
                OperationLog.objects.create(
                    user=request.user,
                    action="return",
                    detail=detail,
                    ip_address=_get_client_ip(request),
                )
            except Exception:
                pass

        if _is_ajax(request):
            result_data = {
                "record_id": record.id,
                "return_date": return_date.strftime("%Y-%m-%d %H:%M"),
            }
            if overdue_days > 0:
                result_data["overdue_days"] = overdue_days
                result_data["fine_amount"] = float(fine_amount)
            return _json_response(200, "归还确认成功", result_data)

        messages.success(request, f"已确认归还《{record.book.title}》")
        return redirect("borrow_manage")

    except Exception as e:
        if _is_ajax(request):
            return _json_response(500, f"归还确认失败: {str(e)}")
        messages.error(request, f"归还确认失败: {str(e)}")
        return redirect("borrow_manage")


@login_required
def overdue_check_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        now = timezone.now()
        overdue_records = BorrowRecord.objects.select_related("book", "user").filter(
            status="borrowing",
            due_date__lt=now,
        )

        updated_count = 0
        fine_per_day = _get_config_value("FINE_PER_DAY", 0.50)

        for record in overdue_records:
            try:
                with transaction.atomic():
                    record = BorrowRecord.objects.select_for_update().get(id=record.id)
                    if record.status != "borrowing":
                        continue

                    record.status = "overdue"
                    delta = now - record.due_date
                    overdue_days = delta.days + 1
                    fine_amount = overdue_days * fine_per_day
                    record.fine_amount = fine_amount
                    record.save(update_fields=["status", "fine_amount"])

                    update_user = User.objects.select_for_update().get(id=record.user_id)
                    update_user.total_fine += fine_amount
                    update_user.save(update_fields=["total_fine"])

                    FineRecord.objects.create(
                        user=update_user,
                        borrow_record=record,
                        fine_amount=fine_amount,
                        overdue_days=overdue_days,
                        is_paid=False,
                    )

                    try:
                        OperationLog.objects.create(
                            user=request.user,
                            action="return",
                            detail=f"系统自动标记逾期: 《{record.book.title}》，借阅人 {record.user.username}，逾期 {overdue_days} 天，罚款 {fine_amount} 元",
                            ip_address=_get_client_ip(request),
                        )
                    except Exception:
                        pass

                    updated_count += 1
            except Exception:
                continue

        return _json_response(200, f"逾期检查完成，共更新 {updated_count} 条记录", {"count": updated_count})

    except Exception as e:
        return _json_response(500, f"逾期检查失败: {str(e)}")


@login_required
def pay_fine_view(request, record_id):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    if request.method != "POST":
        return _json_response(405, "请求方法不允许")

    try:
        try:
            fine_record = FineRecord.objects.select_related("borrow_record__book", "user").get(id=record_id)
        except FineRecord.DoesNotExist:
            if _is_ajax(request):
                return _json_response(404, "罚款记录不存在")
            messages.error(request, "罚款记录不存在")
            return redirect("fine_manage")

        if fine_record.is_paid:
            if _is_ajax(request):
                return _json_response(400, "该罚款已结清")
            messages.error(request, "该罚款已结清")
            return redirect("fine_manage")

        now = timezone.now()

        with transaction.atomic():
            fine_record = FineRecord.objects.select_for_update().get(id=record_id)
            if fine_record.is_paid:
                if _is_ajax(request):
                    return _json_response(400, "该罚款已结清")
                messages.error(request, "该罚款已结清")
                return redirect("fine_manage")

            fine_record.is_paid = True
            fine_record.paid_at = now
            fine_record.save(update_fields=["is_paid", "paid_at"])

            borrow_record = BorrowRecord.objects.select_for_update().get(id=fine_record.borrow_record_id)
            borrow_record.is_paid = True
            borrow_record.save(update_fields=["is_paid"])

            update_user = User.objects.select_for_update().get(id=fine_record.user_id)
            update_user.total_fine = max(0, update_user.total_fine - fine_record.fine_amount)
            update_user.save(update_fields=["total_fine"])

            try:
                OperationLog.objects.create(
                    user=request.user,
                    action="pay_fine",
                    detail=f"缴纳罚款: 《{borrow_record.book.title}》，金额 {fine_record.fine_amount} 元，借阅人 {update_user.username}",
                    ip_address=_get_client_ip(request),
                )
            except Exception:
                pass

        if _is_ajax(request):
            return _json_response(200, "罚款结清成功", {
                "fine_id": fine_record.id,
                "paid_at": now.strftime("%Y-%m-%d %H:%M"),
            })

        messages.success(request, "罚款已结清")
        return redirect("fine_manage")

    except Exception as e:
        if _is_ajax(request):
            return _json_response(500, f"罚款结清失败: {str(e)}")
        messages.error(request, f"罚款结清失败: {str(e)}")
        return redirect("fine_manage")


@login_required
def fine_manage_view(request):
    admin_check = _admin_required(request)
    if admin_check:
        return admin_check

    try:
        queryset = FineRecord.objects.select_related("user", "borrow_record__book").all()

        q = request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(user__username__icontains=q) | Q(borrow_record__book__title__icontains=q)
            )

        paid_filter = request.GET.get("paid", "").strip()
        if paid_filter == "1":
            queryset = queryset.filter(is_paid=True)
        elif paid_filter == "0":
            queryset = queryset.filter(is_paid=False)

        paginator = Paginator(queryset.order_by("-created_at"), 15)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        context = {
            "fines": page_obj,
            "q": q,
            "paid_filter": paid_filter,
        }
        return render(request, "borrow/fine_manage.html", context)

    except Exception as e:
        messages.error(request, f"获取罚款记录失败: {str(e)}")
        return render(request, "borrow/fine_manage.html", {"fines": []})