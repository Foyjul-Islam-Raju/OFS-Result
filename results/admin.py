from django.contrib import admin

from .models import Mark, ResultPublication


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ("student", "exam_subject", "obtained_mark", "is_absent", "updated_at")
    list_filter = ("is_absent", "exam_subject__exam", "exam_subject__classroom")
    search_fields = ("student__student_id", "student__name")
    autocomplete_fields = ("student",)


@admin.register(ResultPublication)
class ResultPublicationAdmin(admin.ModelAdmin):
    list_display = ("exam", "classroom", "section", "is_published", "published_at")
    list_filter = ("is_published", "exam", "classroom")
