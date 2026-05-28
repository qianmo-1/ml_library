from django.urls import path
from . import views

urlpatterns = [
    path("", views.system_config_view, name="system_config"),
    path("config/", views.system_config_view, name="system_config_alt"),
    path("logs/", views.system_logs_view, name="system_logs"),
    path("backup/", views.system_backup_view, name="system_backup"),
    path("backup/download/<str:filename>/", views.download_backup_view, name="download_backup"),
    path("backup/delete/<str:filename>/", views.delete_backup_view, name="delete_backup"),
]