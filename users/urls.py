from django.urls import path
from . import views

urlpatterns = [
    path("", views.index_view, name="index"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("reset-password/", views.reset_password_view, name="reset_password"),
    path("profile/", views.profile_view, name="profile"),
    path("my-borrows/", views.my_borrows_view, name="my_borrows"),
    path("my-fines/", views.my_fines_view, name="my_fines"),
    path("users/manage/", views.manage_users_view, name="manage_users"),
    path("users/edit/<int:user_id>/", views.edit_user_view, name="edit_user"),
    path("users/freeze/<int:user_id>/", views.freeze_user_view, name="freeze_user"),
    path("users/unfreeze/<int:user_id>/", views.unfreeze_user_view, name="unfreeze_user"),
    path("users/reset-password/<int:user_id>/", views.admin_reset_password_view, name="admin_reset_password"),
]