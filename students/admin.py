from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "name", "classroom", "section", "roll", "is_active")
    list_filter = ("classroom", "section", "is_active")
    search_fields = ("student_id", "name")
    ordering = ("classroom__display_order", "roll")
