from django import forms

from academics.forms import BootstrapFormMixin
from academics.models import Section

from .models import Student


class StudentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Student
        fields = ["student_id", "name", "classroom", "section", "roll", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = Section.objects.select_related("classroom")
        self.fields["section"].required = False
        self.fields["student_id"].widget.attrs["placeholder"] = "6001"
        self.fields["name"].widget.attrs["placeholder"] = "Rahim Ahmed"

    def clean_student_id(self):
        return self.cleaned_data["student_id"].strip()

    def clean(self):
        cleaned = super().clean()
        classroom = cleaned.get("classroom")
        section = cleaned.get("section")
        if classroom and section and section.classroom_id != classroom.id:
            self.add_error("section", "This section does not belong to the selected class.")
        return cleaned
