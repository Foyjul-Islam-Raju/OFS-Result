from django.contrib import admin

from .models import (
    ClassRoom,
    ClassSubject,
    Exam,
    ExamSubject,
    ExamType,
    Section,
    Semester,
    Subject,
)


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    search_fields = ("name",)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("classroom", "name", "is_active")
    list_filter = ("classroom",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "display_order", "is_active")
    search_fields = ("name", "code")


@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = (
        "classroom", "subject", "default_full_mark", "credit", "is_optional", "is_active",
    )
    list_filter = ("classroom", "is_optional", "is_active")
    search_fields = ("subject__name",)


@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "uses_cgpa", "show_letter_grade", "is_active")


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_year", "display_order", "is_active")
    list_filter = ("academic_year",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "name", "academic_year", "exam_type", "semester", "status", "start_date", "end_date",
    )
    list_filter = ("status", "exam_type", "academic_year")
    search_fields = ("name",)


@admin.register(ExamSubject)
class ExamSubjectAdmin(admin.ModelAdmin):
    list_display = ("exam", "classroom", "subject", "full_mark", "pass_mark", "credit")
    list_filter = ("exam", "classroom", "subject")
