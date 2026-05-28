from django.urls import path
from . import views

urlpatterns = [
    path("", views.stats_dashboard_view, name="stats_dashboard"),
    path("dashboard/", views.stats_dashboard_view, name="stats_dashboard_alt"),
    path("hot-books/", views.stats_hot_books_view, name="stats_hot_books"),
    path("inventory/", views.stats_inventory_view, name="stats_inventory"),
    path("export/borrows/", views.stats_export_borrows_view, name="stats_export_borrows"),
    path("export/books/", views.stats_export_books_view, name="stats_export_books"),
    path("export/users/", views.stats_export_users_view, name="stats_export_users"),
]