from django import forms

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


class BootstrapFormMixin:
    """Applies Bootstrap classes without repeating widget attrs everywhere."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class ClassRoomForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ClassRoom
        fields = ["name", "display_order", "is_active"]


class SectionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Section
        fields = ["classroom", "name", "is_active"]


class SubjectForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "code", "display_order", "is_active"]


class ClassSubjectForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ClassSubject
        fields = [
            "classroom",
            "subject",
            "default_full_mark",
            "credit",
            "is_optional",
            "display_order",
            "is_active",
        ]


class ClassSubjectBulkForm(BootstrapFormMixin, forms.Form):
    """Assign several subjects to a class in one go."""

    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.filter(is_active=True),
        label="Class",
        empty_label="Select class",
    )
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="Subjects studied by this class",
        help_text="Tick as many as the class studies. Six, ten, any number.",
    )
    default_full_mark = forms.IntegerField(min_value=1, initial=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subjects"].widget.attrs.pop("class", None)


class ExamTypeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ExamType
        fields = ["name", "uses_cgpa", "show_letter_grade", "is_active"]


class SemesterForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Semester
        fields = ["name", "academic_year", "display_order", "is_active"]


class ExamForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            "name",
            "academic_year",
            "exam_type",
            "semester",
            "pass_percentage",
            "start_date",
            "end_date",
            "status",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be earlier than the start date.")

        exam_type = cleaned.get("exam_type")
        semester = cleaned.get("semester")
        if exam_type and exam_type.uses_cgpa and not semester:
            self.add_error(
                "semester", "Semester examinations need a semester so CGPA can be grouped."
            )
        if semester and not (exam_type and exam_type.uses_cgpa):
            self.add_error(
                "semester", "Only semester examinations use a semester. Clear this field."
            )
        return cleaned


class ExamSubjectForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ExamSubject
        fields = [
            "exam",
            "classroom",
            "subject",
            "full_mark",
            "pass_mark",
            "credit",
            "display_order",
        ]

    def clean(self):
        cleaned = super().clean()
        full_mark = cleaned.get("full_mark")
        pass_mark = cleaned.get("pass_mark")
        if full_mark and pass_mark is not None and pass_mark > full_mark:
            self.add_error("pass_mark", "Pass mark cannot be greater than the full mark.")
        return cleaned


class ExamSetupForm(BootstrapFormMixin, forms.Form):
    """Builds the exam's subject list from the class curriculum, then lets the
    admin untick anything the exam was not conducted in."""

    exam = forms.ModelChoiceField(queryset=Exam.objects.all(), empty_label="Select exam")
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.filter(is_active=True),
        label="Class",
        empty_label="Select class",
    )
