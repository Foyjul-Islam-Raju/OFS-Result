from django.urls import path

from . import portal_views

app_name = "portal"

urlpatterns = [
    path("", portal_views.lookup, name="lookup"),
    path("results/", portal_views.exam_list, name="exam_list"),
    path("results/<int:exam_id>/", portal_views.result_detail, name="result"),
    path("results/<int:exam_id>/print/", portal_views.result_print, name="result_print"),
    path("exit/", portal_views.sign_out, name="sign_out"),
]
