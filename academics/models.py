"""Academic structure.

Nothing here assumes a fixed number of subjects. A class has as many subjects
as there are rows in ClassSubject, and an exam covers as many subjects as there
are rows in ExamSubject. Six today, ten next year, no code change.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class ClassRoom(models.Model):
    """A class/grade such as `Class 6` or `Nursery`."""

    name = models.CharField(max_length=60, unique=True)
    display_order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers appear first in lists."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "class"
        verbose_name_plural = "classes"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("academics:class_list")


class Section(models.Model):
    """An optional subdivision of a class, e.g. `A`, `B`, `C`."""

    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name="sections"
    )
    name = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["classroom__display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "name"], name="uniq_section_per_class"
            )
        ]

    def __str__(self) -> str:
        return f"{self.classroom.name} - {self.name}"

    def get_absolute_url(self) -> str:
        return reverse("academics:section_list")


class Subject(models.Model):
    """The school-wide catalogue of subject names."""

    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=20, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("academics:subject_list")


class ClassSubject(models.Model):
    """The curriculum: which subjects a class studies, and how many.

    Class 6 might have six rows here and Class 9 ten. This is what makes the
    subject list per class fully data-driven.
    """

    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name="class_subjects"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="class_subjects"
    )
    default_full_mark = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Used as the starting full mark when you set up an exam.",
    )
    credit = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1,
        help_text="Only used for CGPA on semester exams. Leave at 1 otherwise.",
    )
    is_optional = models.BooleanField(
        default=False, help_text="Optional/4th subject."
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["classroom__display_order", "display_order", "subject__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "subject"], name="uniq_subject_per_class"
            )
        ]
        indexes = [models.Index(fields=["classroom", "is_active"])]
        verbose_name = "class subject"

    def __str__(self) -> str:
        return f"{self.classroom.name} — {self.subject.name}"

    def get_absolute_url(self) -> str:
        return reverse("academics:classsubject_list")


class ExamType(models.Model):
    """Regular/class exam, semester exam, or anything the school invents later.

    The two switches decide how a result is presented, so adding a new style of
    exam is an admin task rather than a code change.
    """

    name = models.CharField(max_length=80, unique=True)
    uses_cgpa = models.BooleanField(
        default=False,
        verbose_name="Semester type (calculate GPA and CGPA)",
        help_text="Turn on only for semester examinations.",
    )
    show_letter_grade = models.BooleanField(
        default=False,
        help_text="Regular class exams show marks and percentage only, no letter grades.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "exam type"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("academics:examtype_list")


class Semester(models.Model):
    """Semester information, used to group semester exams for CGPA."""

    name = models.CharField(max_length=80, help_text="Example: Semester 1")
    academic_year = models.PositiveIntegerField(validators=[MinValueValidator(1900)])
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["academic_year", "display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "academic_year"], name="uniq_semester_per_year"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.academic_year}"

    def get_absolute_url(self) -> str:
        return reverse("academics:semester_list")


class Exam(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    name = models.CharField(max_length=120)
    academic_year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)], help_text="Example: 2026"
    )
    exam_type = models.ForeignKey(
        ExamType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
        help_text="Leave blank to treat this as a regular class exam.",
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
        help_text="Only for semester examinations.",
    )
    pass_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Leave blank to use the school-wide passing criteria from Settings.",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-academic_year", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "academic_year"], name="uniq_exam_per_year"
            )
        ]
        indexes = [models.Index(fields=["status", "academic_year"])]

    def __str__(self) -> str:
        return f"{self.name} {self.academic_year}"

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED

    @property
    def is_semester(self) -> bool:
        """No exam type set means a plain class exam."""
        return bool(self.exam_type and self.exam_type.uses_cgpa)

    @property
    def shows_letter_grade(self) -> bool:
        return bool(self.exam_type and self.exam_type.show_letter_grade)

    def get_absolute_url(self) -> str:
        return reverse("academics:exam_list")


class ExamSubject(models.Model):
    """Which subjects an exam was actually conducted in, for one class.

    A subject only appears on a student's result if a row exists here. So if
    Class 9 studies ten subjects but only eight were examined, the result shows
    those eight.
    """

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="exam_subjects")
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name="exam_subjects"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="exam_subjects"
    )
    full_mark = models.PositiveIntegerField(
        default=100, validators=[MinValueValidator(1)]
    )
    pass_mark = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Leave blank to use the percentage-based passing criteria.",
    )
    credit = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1,
        help_text="Weight used for GPA/CGPA on semester exams.",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "subject__display_order", "subject__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "classroom", "subject"],
                name="uniq_subject_per_exam_class",
            )
        ]
        indexes = [models.Index(fields=["exam", "classroom"])]
        verbose_name = "exam subject"

    def __str__(self) -> str:
        return f"{self.exam} / {self.classroom} / {self.subject} ({self.full_mark})"

    def get_absolute_url(self) -> str:
        return reverse("academics:examsubject_list")
