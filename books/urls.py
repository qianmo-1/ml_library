from django.urls import path
from . import views

urlpatterns = [
    path("", views.book_list_view, name="book_list"),
    path("list/", views.book_list_view, name="book_list_alt"),
    path("reading-room/", views.reading_room_view, name="reading_room"),
    path("read/<int:book_id>/", views.book_reader_view, name="book_reader"),
    path("detail/<int:book_id>/", views.book_detail_view, name="book_detail"),
    path("chapter/<int:book_id>/<int:chapter_index>/", views.chapter_content_view, name="chapter_content"),
    path("manage/", views.book_manage_view, name="book_manage"),
    path("add/", views.book_add_view, name="book_add"),
    path("edit/<int:book_id>/", views.book_edit_view, name="book_edit"),
    path("delete/<int:book_id>/", views.book_delete_view, name="book_delete"),
    path("batch-delete/", views.book_batch_delete_view, name="book_batch_delete"),
    path("category/", views.category_manage_view, name="category_manage"),
    path("category/add/", views.category_add_view, name="category_add"),
    path("category/edit/<int:cat_id>/", views.category_edit_view, name="category_edit"),
    path("category/delete/<int:cat_id>/", views.category_delete_view, name="category_delete"),
]