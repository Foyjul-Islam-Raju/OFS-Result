from decimal import Decimal, InvalidOperation

from django import forms

from academics.forms import BootstrapFormMixin
from academics.models import ClassRoom, Exam, ExamSubject, Section

from .models import Mark


class MarkEntrySelectForm(BootstrapFormMixin, forms.Form):
    exam = forms.ModelChoiceField(queryset=Exam.objects.all(), empty_label="Select exam")
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.filter(is_active=True),
        empty_label="Select class",
        label="Class",
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.select_related("classroom"),
        required=False,
        empty_label="All sections",
    )


class MarkGridForm(forms.Form):
    """Dynamically builds one numeric field + one absent checkbox per
    student/subject cell, and validates everything server-side."""

    def __init__(self, *args, students=None, exam_subjects=None, existing=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.students = students or []
        self.exam_subjects = exam_subjects or []
        existing = existing or {}
        for student in self.students:
            for exam_subject in self.exam_subjects:
                mark = existing.get((student.id, exam_subject.id))
                mark_key = f"mark_{student.id}_{exam_subject.id}"
                absent_key = f"absent_{student.id}_{exam_subject.id}"
                self.fields[mark_key] = forms.DecimalField(
                    required=False,
                    min_value=Decimal("0"),
                    max_value=Decimal(exam_subject.full_mark),
                    max_digits=6,
                    decimal_places=2,
                    initial=None if (mark and mark.is_absent) else (mark.obtained_mark if mark else None),
                    widget=forms.NumberInput(
                        attrs={
                            "class": "form-control mark-input",
                            "step": "0.01",
                            "min": "0",
                            "max": exam_subject.full_mark,
                            "data-full-mark": exam_subject.full_mark,
                            "inputmode": "decimal",
                        }
                    ),
                )
                self.fields[absent_key] = forms.BooleanField(
                    required=False,
                    initial=bool(mark and mark.is_absent),
                    widget=forms.CheckboxInput(attrs={"class": "form-check-input absent-toggle"}),
                )

    def cell(self, student, exam_subject):
        return {
            "mark": self[f"mark_{student.id}_{exam_subject.id}"],
            "absent": self[f"absent_{student.id}_{exam_subject.id}"],
        }

    def clean(self):
        cleaned = super().clean()
        for student in self.students:
            for exam_subject in self.exam_subjects:
                mark_key = f"mark_{student.id}_{exam_subject.id}"
                absent_key = f"absent_{student.id}_{exam_subject.id}"
                value = cleaned.get(mark_key)
                absent = cleaned.get(absent_key)
                label = f"{student.name} / {exam_subject.subject.name}"
                if absent and value is not None:
                    self.add_error(
                        mark_key,
                        f"{label}: an absent student cannot also have a mark.",
                    )
                    continue
                if value is None:
                    continue
                if value < 0:
                    self.add_error(mark_key, f"{label}: marks cannot be negative.")
                elif value > exam_subject.full_mark:
                    self.add_error(
                        mark_key,
                        f"{label}: obtained mark cannot be greater than Full Mark "
                        f"({exam_subject.full_mark}).",
                    )
        return cleaned

    def iter_cells(self):
        for student in self.students:
            yield student, [self.cell(student, es) for es in self.exam_subjects]


class StudentLookupForm(forms.Form):
    """The only thing a student ever fills in: ID + class."""

    student_id = forms.CharField(
        max_length=30,
        label="Student ID",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "e.g. 6001",
                "autocomplete": "off",
                "autofocus": "autofocus",
            }
        ),
    )
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.filter(is_active=True),
        label="Class",
        empty_label="Select your class",
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
    )

    def clean_student_id(self):
        return self.cleaned_data["student_id"].strip()
