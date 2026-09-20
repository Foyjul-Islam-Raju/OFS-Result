from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from academics.models import ClassRoom, Section


class StudentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def in_class(self, classroom):
        return self.filter(classroom=classroom)


class Student(models.Model):
    student_id = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Unique identifier the student types in to see a result, e.g. 6001.",
    )
    name = models.CharField(max_length=120)
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.PROTECT, related_name="students"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    roll = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StudentQuerySet.as_manager()

    class Meta:
        ordering = ["classroom__display_order", "section__name", "roll", "name"]
        indexes = [
            models.Index(fields=["classroom", "section"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.student_id} - {self.name}"

    def clean(self):
        super().clean()
        if self.section_id and self.classroom_id:
            if self.section.classroom_id != self.classroom_id:
                raise ValidationError(
                    {"section": "The selected section does not belong to this class."}
                )

    def save(self, *args, **kwargs):
        self.student_id = self.student_id.strip()
        super().save(*args, **kwargs)

    @property
    def class_label(self) -> str:
        if self.section:
            return f"{self.classroom.name} ({self.section.name})"
        return self.classroom.name

    def get_absolute_url(self) -> str:
        return reverse("students:list")
