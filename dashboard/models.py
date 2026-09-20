from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SiteSetting(models.Model):
    """Single row of institution-wide configuration.

    Keeping the pass rule and position toggle in the database means the school
    can change policy later without touching the code.
    """

    institution_name = models.CharField(max_length=160, default="Online Foundation School")
    institution_tagline = models.CharField(
        max_length=160, blank=True, default="Result Portal"
    )
    address = models.CharField(max_length=200, blank=True)
    pass_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=33,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage a student needs in every subject to pass.",
    )
    require_pass_in_every_subject = models.BooleanField(
        default=True,
        help_text="If on, failing one subject fails the whole result.",
    )
    absent_counts_as_fail = models.BooleanField(
        default=True, help_text="Treat an absent subject as a failed subject."
    )
    fail_zeroes_gpa = models.BooleanField(
        default=True,
        verbose_name="Failing a subject makes GPA 0.00",
        help_text="Semester exams only. Turn off to average the grade points instead.",
    )
    show_position = models.BooleanField(
        default=False, help_text="Show class position on the student result page."
    )
    section_wise_highest = models.BooleanField(
        default=False,
        help_text="Calculate highest marks and position within the section instead of the whole class.",
    )
    result_footer_note = models.CharField(
        max_length=200,
        blank=True,
        default="This is a computer generated result sheet.",
    )

    class Meta:
        verbose_name = "site setting"
        verbose_name_plural = "site settings"

    def __str__(self) -> str:
        return self.institution_name

    @classmethod
    def load(cls) -> "SiteSetting":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - guard only
        return
