from django.core.validators import MinValueValidator
from django.db import models

from academics.models import ClassRoom, Exam, ExamSubject, Section
from students.models import Student


class Mark(models.Model):
    """One subject mark for one student in one exam.

    `exam_subject` already encodes exam + class + subject + full mark, so a
    unique constraint on (student, exam_subject) prevents duplicate records for
    the same student/exam/subject combination.
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="marks")
    exam_subject = models.ForeignKey(
        ExamSubject, on_delete=models.CASCADE, related_name="marks"
    )
    obtained_mark = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Leave blank when the student was absent.",
    )
    is_absent = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marks_entered",
    )

    class Meta:
        ordering = ["exam_subject__display_order", "student__roll"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "exam_subject"], name="uniq_mark_per_student_subject"
            ),
            models.CheckConstraint(
                condition=models.Q(obtained_mark__gte=0) | models.Q(obtained_mark__isnull=True),
                name="mark_not_negative",
            ),
        ]
        indexes = [models.Index(fields=["exam_subject", "is_absent"])]

    def __str__(self) -> str:
        value = "Absent" if self.is_absent else self.obtained_mark
        return f"{self.student.student_id} / {self.exam_subject.subject} = {value}"

    @property
    def effective_mark(self):
        """Mark used for totals. Absent contributes nothing."""
        if self.is_absent or self.obtained_mark is None:
            return 0
        return self.obtained_mark


class ResultPublication(models.Model):
    """Publish state for one exam + class (optionally one section).

    Students only see a result when both the exam status is Published and the
    matching publication row is published.
    """

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="publications")
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name="publications"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="publications",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-published_at", "classroom__display_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "classroom", "section"],
                name="uniq_publication_with_section",
                condition=models.Q(section__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["exam", "classroom"],
                name="uniq_publication_without_section",
                condition=models.Q(section__isnull=True),
            ),
        ]
        verbose_name = "result publication"

    def __str__(self) -> str:
        label = f"{self.exam} / {self.classroom}"
        if self.section:
            label += f" ({self.section.name})"
        return label
