from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from academics.models import ClassRoom, Section

from .forms import StudentForm
from .models import Student


class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = "students/student_list.html"
    context_object_name = "students"
    paginate_by = 25

    def get_queryset(self):
        queryset = Student.objects.select_related("classroom", "section")
        search = self.request.GET.get("q", "").strip()
        classroom = self.request.GET.get("classroom")
        section = self.request.GET.get("section")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(student_id__icontains=search)
            )
        if classroom:
            queryset = queryset.filter(classroom_id=classroom)
        if section:
            queryset = queryset.filter(section_id=section)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "classes": ClassRoom.objects.all(),
                "sections": Section.objects.select_related("classroom"),
                "search": self.request.GET.get("q", ""),
                "selected_class": self.request.GET.get("classroom", ""),
                "selected_section": self.request.GET.get("section", ""),
            }
        )
        return context


class StudentCreateView(LoginRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "partials/object_form.html"
    extra_context = {"page_title": "Add student", "back_url_name": "students:list"}

    def form_valid(self, form):
        messages.success(self.request, "Student saved.")
        return super().form_valid(form)


class StudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "partials/object_form.html"
    extra_context = {"page_title": "Edit student", "back_url_name": "students:list"}

    def form_valid(self, form):
        messages.success(self.request, "Student updated.")
        return super().form_valid(form)


class StudentDeleteView(LoginRequiredMixin, DeleteView):
    model = Student
    template_name = "partials/confirm_delete.html"
    success_url = reverse_lazy("students:list")

    def form_valid(self, form):
        messages.success(self.request, f"{self.object} deleted.")
        return super().form_valid(form)
