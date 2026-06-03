from django.urls import path
from . import views

urlpatterns = [
    path("book/<int:book_id>/", views.borrow_book_view, name="borrow_book"),
    path("renew/<int:record_id>/", views.renew_book_view, name="renew_book"),
    path("return/<int:record_id>/", views.return_book_view, name="return_book"),
    path("manage/", views.borrow_manage_view, name="borrow_manage"),
    path("confirm-return/<int:record_id>/", views.confirm_return_view, name="confirm_return"),
    path("overdue-check/", views.overdue_check_view, name="overdue_check"),
    path("pay-fine/<int:record_id>/", views.pay_fine_view, name="pay_fine"),
    path("fines/", views.fine_manage_view, name="fine_manage"),
]