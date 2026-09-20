from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import (
    ClassRoomForm,
    ClassSubjectBulkForm,
    ClassSubjectForm,
    ExamForm,
    ExamSetupForm,
    ExamSubjectForm,
    ExamTypeForm,
    SectionForm,
    SemesterForm,
    SubjectForm,
)
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


class AdminMixin(LoginRequiredMixin):
    """Every academics screen needs a signed-in staff user."""


class MessageMixin:
    success_message = "Saved."

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response


class ObjectDeleteView(AdminMixin, DeleteView):
    template_name = "partials/confirm_delete.html"

    def form_valid(self, form):
        messages.success(self.request, f"{self.object} deleted.")
        return super().form_valid(form)


# ---------------------------------------------------------------- classes
class ClassListView(AdminMixin, ListView):
    model = ClassRoom
    template_name = "academics/class_list.html"
    context_object_name = "classes"

    def get_queryset(self):
        return ClassRoom.objects.annotate(
            student_count=Count("students", filter=Q(students__is_active=True), distinct=True),
            section_count=Count("sections", distinct=True),
        )


class ClassCreateView(AdminMixin, MessageMixin, CreateView):
    model = ClassRoom
    form_class = ClassRoomForm
    template_name = "partials/object_form.html"
    success_message = "Class saved."
    extra_context = {"page_title": "Add class", "back_url_name": "academics:class_list"}


class ClassUpdateView(AdminMixin, MessageMixin, UpdateView):
    model = ClassRoom
    form_class = ClassRoomForm
    template_name = "partials/object_form.html"
    success_message = "Class updated."
    extra_context = {"page_title": "Edit class", "back_url_name": "academics:class_list"}


class ClassDeleteView(ObjectDeleteView):
    model = ClassRoom
    success_url = reverse_lazy("academics:class_list")


# --------------------------------------------------------------- sections
class SectionListView(AdminMixin, ListView):
    model = Section
    template_name = "academics/section_list.html"
    context_object_name = "sections"
    queryset = Section.objects.select_related("classroom")


class SectionCreateView(AdminMixin, MessageMixin, CreateView):
    model = Section
    form_class = SectionForm
    template_name = "partials/object_form.html"
    success_message = "Section saved."
    extra_context = {"page_title": "Add section", "back_url_name": "academics:section_list"}


class SectionUpdateView(AdminMixin, MessageMixin, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = "partials/object_form.html"
    success_message = "Section updated."
    extra_context = {"page_title": "Edit section", "back_url_name": "academics:section_list"}


class SectionDeleteView(ObjectDeleteView):
    model = Section
    success_url = reverse_lazy("academics:section_list")


# --------------------------------------------------------------- subjects
class SubjectListView(AdminMixin, ListView):
    model = Subject
    template_name = "academics/subject_list.html"
    context_object_name = "subjects"


class SubjectCreateView(AdminMixin, MessageMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = "partials/object_form.html"
    success_message = "Subject saved."
    extra_context = {"page_title": "Add subject", "back_url_name": "academics:subject_list"}


class SubjectUpdateView(AdminMixin, MessageMixin, UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = "partials/object_form.html"
    success_message = "Subject updated."
    extra_context = {"page_title": "Edit subject", "back_url_name": "academics:subject_list"}


class SubjectDeleteView(ObjectDeleteView):
    model = Subject
    success_url = reverse_lazy("academics:subject_list")


# ------------------------------------------------------------------ exams
class ExamListView(AdminMixin, ListView):
    model = Exam
    template_name = "academics/exam_list.html"
    context_object_name = "exams"

    def get_queryset(self):
        queryset = Exam.objects.annotate(subject_count=Count("exam_subjects"))
        year = self.request.GET.get("year")
        if year:
            queryset = queryset.filter(academic_year=year)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["years"] = (
            Exam.objects.values_list("academic_year", flat=True).distinct().order_by("-academic_year")
        )
        return context


class ExamCreateView(AdminMixin, MessageMixin, CreateView):
    model = Exam
    form_class = ExamForm
    template_name = "partials/object_form.html"
    success_message = "Exam saved."
    extra_context = {"page_title": "Add exam", "back_url_name": "academics:exam_list"}


class ExamUpdateView(AdminMixin, MessageMixin, UpdateView):
    model = Exam
    form_class = ExamForm
    template_name = "partials/object_form.html"
    success_message = "Exam updated."
    extra_context = {"page_title": "Edit exam", "back_url_name": "academics:exam_list"}


class ExamDeleteView(ObjectDeleteView):
    model = Exam
    success_url = reverse_lazy("academics:exam_list")


# ---------------------------------------------------- exam subject set-up
class ExamSubjectListView(AdminMixin, ListView):
    model = ExamSubject
    template_name = "academics/examsubject_list.html"
    context_object_name = "exam_subjects"

    def get_queryset(self):
        queryset = ExamSubject.objects.select_related("exam", "classroom", "subject")
        exam = self.request.GET.get("exam")
        classroom = self.request.GET.get("classroom")
        if exam:
            queryset = queryset.filter(exam_id=exam)
        if classroom:
            queryset = queryset.filter(classroom_id=classroom)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["exams"] = Exam.objects.all()
        context["classes"] = ClassRoom.objects.all()
        context["selected_exam"] = self.request.GET.get("exam", "")
        context["selected_class"] = self.request.GET.get("classroom", "")
        return context


class ExamSubjectCreateView(AdminMixin, MessageMixin, CreateView):
    model = ExamSubject
    form_class = ExamSubjectForm
    template_name = "partials/object_form.html"
    success_message = "Full mark saved."
    extra_context = {
        "page_title": "Add exam subject",
        "back_url_name": "academics:examsubject_list",
    }


class ExamSubjectUpdateView(AdminMixin, MessageMixin, UpdateView):
    model = ExamSubject
    form_class = ExamSubjectForm
    template_name = "partials/object_form.html"
    success_message = "Full mark updated."
    extra_context = {
        "page_title": "Edit exam subject",
        "back_url_name": "academics:examsubject_list",
    }


class ExamSubjectDeleteView(ObjectDeleteView):
    model = ExamSubject
    success_url = reverse_lazy("academics:examsubject_list")


# ------------------------------------------------- subjects assigned to a class
class ClassSubjectListView(AdminMixin, ListView):
    model = ClassSubject
    template_name = "academics/classsubject_list.html"
    context_object_name = "class_subjects"

    def get_queryset(self):
        queryset = ClassSubject.objects.select_related("classroom", "subject")
        classroom = self.request.GET.get("classroom")
        if classroom:
            queryset = queryset.filter(classroom_id=classroom)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["classes"] = ClassRoom.objects.annotate(
            subject_count=Count("class_subjects", filter=Q(class_subjects__is_active=True))
        )
        context["selected_class"] = self.request.GET.get("classroom", "")
        context["bulk_form"] = ClassSubjectBulkForm()
        return context


class ClassSubjectCreateView(AdminMixin, MessageMixin, CreateView):
    model = ClassSubject
    form_class = ClassSubjectForm
    template_name = "partials/object_form.html"
    success_message = "Subject assigned to the class."
    extra_context = {
        "page_title": "Assign a subject to a class",
        "back_url_name": "academics:classsubject_list",
    }


class ClassSubjectUpdateView(AdminMixin, MessageMixin, UpdateView):
    model = ClassSubject
    form_class = ClassSubjectForm
    template_name = "partials/object_form.html"
    success_message = "Class subject updated."
    extra_context = {
        "page_title": "Edit class subject",
        "back_url_name": "academics:classsubject_list",
    }


class ClassSubjectDeleteView(ObjectDeleteView):
    model = ClassSubject
    success_url = reverse_lazy("academics:classsubject_list")


@login_required
@require_POST
def classsubject_bulk(request):
    """Tick several subjects and assign them to a class at once."""
    form = ClassSubjectBulkForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Pick a class and at least one subject.")
        return redirect("academics:classsubject_list")

    classroom = form.cleaned_data["classroom"]
    full_mark = form.cleaned_data["default_full_mark"]
    created = 0
    for order, subject in enumerate(form.cleaned_data["subjects"], start=1):
        _, made = ClassSubject.objects.get_or_create(
            classroom=classroom,
            subject=subject,
            defaults={"default_full_mark": full_mark, "display_order": order},
        )
        created += int(made)
    messages.success(
        request,
        f"{classroom.name} now studies {classroom.class_subjects.count()} subject(s). "
        f"{created} newly added.",
    )
    return redirect(f"{reverse('academics:classsubject_list')}?classroom={classroom.id}")


# ----------------------------------------------------------------- exam types
class ExamTypeListView(AdminMixin, ListView):
    model = ExamType
    template_name = "academics/examtype_list.html"
    context_object_name = "exam_types"
    queryset = ExamType.objects.annotate(exam_count=Count("exams"))


class ExamTypeCreateView(AdminMixin, MessageMixin, CreateView):
    model = ExamType
    form_class = ExamTypeForm
    template_name = "partials/object_form.html"
    success_message = "Exam type saved."
    extra_context = {"page_title": "Add exam type", "back_url_name": "academics:examtype_list"}


class ExamTypeUpdateView(AdminMixin, MessageMixin, UpdateView):
    model = ExamType
    form_class = ExamTypeForm
    template_name = "partials/object_form.html"
    success_message = "Exam type updated."
    extra_context = {"page_title": "Edit exam type", "back_url_name": "academics:examtype_list"}


class ExamTypeDeleteView(ObjectDeleteView):
    model = ExamType
    success_url = reverse_lazy("academics:examtype_list")


# ------------------------------------------------------------------ semesters
class SemesterListView(AdminMixin, ListView):
    model = Semester
    template_name = "academics/semester_list.html"
    context_object_name = "semesters"
    queryset = Semester.objects.annotate(exam_count=Count("exams"))


class SemesterCreateView(AdminMixin, MessageMixin, CreateView):
    model = Semester
    form_class = SemesterForm
    template_name = "partials/object_form.html"
    success_message = "Semester saved."
    extra_context = {"page_title": "Add semester", "back_url_name": "academics:semester_list"}


class SemesterUpdateView(AdminMixin, MessageMixin, UpdateView):
    model = Semester
    form_class = SemesterForm
    template_name = "partials/object_form.html"
    success_message = "Semester updated."
    extra_context = {"page_title": "Edit semester", "back_url_name": "academics:semester_list"}


class SemesterDeleteView(ObjectDeleteView):
    model = Semester
    success_url = reverse_lazy("academics:semester_list")


# --------------------------------------------- build an exam's subject list
@login_required
def exam_setup(request):
    """Copies the class curriculum into an exam, so the admin only has to
    remove the subjects that were not examined."""
    exam = Exam.objects.filter(pk=request.GET.get("exam") or request.POST.get("exam")).first()
    classroom = ClassRoom.objects.filter(
        pk=request.GET.get("classroom") or request.POST.get("classroom")
    ).first()

    context = {
        "form": ExamSetupForm(initial={"exam": exam, "classroom": classroom}),
        "exam": exam,
        "classroom": classroom,
    }

    if exam and classroom:
        curriculum = list(
            ClassSubject.objects.filter(classroom=classroom, is_active=True)
            .select_related("subject")
        )
        chosen = {
            es.subject_id: es
            for es in ExamSubject.objects.filter(exam=exam, classroom=classroom)
        }
        # Resolve everything the template needs here; templates cannot index
        # a dict by a variable key.
        context["curriculum"] = [
            {
                "subject_id": cs.subject_id,
                "name": cs.subject.name,
                "is_optional": cs.is_optional,
                "credit": cs.credit,
                "checked": cs.subject_id in chosen,
                "full_mark": (
                    chosen[cs.subject_id].full_mark
                    if cs.subject_id in chosen
                    else cs.default_full_mark
                ),
            }
            for cs in curriculum
        ]

        if request.method == "POST":
            keep = set(map(int, request.POST.getlist("subjects")))
            added = removed = 0
            for class_subject in curriculum:
                existing = chosen.get(class_subject.subject_id)
                if class_subject.subject_id in keep and not existing:
                    ExamSubject.objects.create(
                        exam=exam,
                        classroom=classroom,
                        subject=class_subject.subject,
                        full_mark=request.POST.get(
                            f"full_{class_subject.subject_id}"
                        ) or class_subject.default_full_mark,
                        credit=class_subject.credit,
                        display_order=class_subject.display_order,
                    )
                    added += 1
                elif class_subject.subject_id in keep and existing:
                    new_full = request.POST.get(f"full_{class_subject.subject_id}")
                    if new_full and int(new_full) != existing.full_mark:
                        existing.full_mark = int(new_full)
                        existing.save(update_fields=["full_mark"])
                elif class_subject.subject_id not in keep and existing:
                    existing.delete()
                    removed += 1
            messages.success(
                request,
                f"{exam.name} for {classroom.name}: {added} subject(s) added, "
                f"{removed} removed. Marks are only collected for the subjects left ticked.",
            )
            return redirect(
                f"{reverse('academics:exam_setup')}?exam={exam.id}&classroom={classroom.id}"
            )

    return render(request, "academics/exam_setup.html", context)
