from django.urls import path

from . import views

app_name = "results"

urlpatterns = [
    path("mark-entry/", views.mark_entry, name="mark_entry"),
    path("review/", views.review, name="review"),
    path("publish/", views.toggle_publish, name="toggle_publish"),
    path("published/", views.published_list, name="published"),
]
