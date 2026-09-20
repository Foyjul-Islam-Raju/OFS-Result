"""Admin-side result views: mark entry, review, publish/unpublish."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from academics.models import ClassRoom, Exam, ExamSubject, Section
from dashboard.models import SiteSetting
from students.models import Student

from .forms import MarkEntrySelectForm, MarkGridForm
from .models import Mark, ResultPublication
from .services import class_result_sheets, highest_mark_holders


def _selection(request):
    """Reads exam/class/section from the querystring and validates them."""
    exam_id = request.GET.get("exam") or request.POST.get("exam")
    class_id = request.GET.get("classroom") or request.POST.get("classroom")
    section_id = request.GET.get("section") or request.POST.get("section")
    exam = Exam.objects.filter(pk=exam_id).first() if exam_id else None
    classroom = ClassRoom.objects.filter(pk=class_id).first() if class_id else None
    section = None
    if section_id and classroom:
        section = Section.objects.filter(pk=section_id, classroom=classroom).first()
    return exam, classroom, section


@login_required
def mark_entry(request):
    exam, classroom, section = _selection(request)
    select_form = MarkEntrySelectForm(
        initial={"exam": exam, "classroom": classroom, "section": section}
    )
    context = {
        "select_form": select_form,
        "exam": exam,
        "classroom": classroom,
        "section": section,
        "search": request.GET.get("q", "").strip(),
    }

    if not (exam and classroom):
        return render(request, "results/mark_entry.html", context)

    exam_subjects = list(
        ExamSubject.objects.filter(exam=exam, classroom=classroom).select_related("subject")
    )
    students = Student.objects.active().filter(classroom=classroom).select_related("section")
    if section:
        students = students.filter(section=section)
    if context["search"]:
        from django.db.models import Q

        students = students.filter(
            Q(name__icontains=context["search"]) | Q(student_id__icontains=context["search"])
        )
    students = list(students)

    existing = {
        (m.student_id, m.exam_subject_id): m
        for m in Mark.objects.filter(student__in=students, exam_subject__in=exam_subjects)
    }

    if request.method == "POST":
        form = MarkGridForm(
            request.POST,
            students=students,
            exam_subjects=exam_subjects,
            existing=existing,
        )
        if form.is_valid():
            saved = _save_marks(request, form, students, exam_subjects, existing)
            messages.success(request, f"Saved {saved} mark(s) as draft.")
            query = f"?exam={exam.id}&classroom={classroom.id}"
            if section:
                query += f"&section={section.id}"
            if request.POST.get("next") == "review":
                return redirect(reverse("results:review") + query)
            return redirect(reverse("results:mark_entry") + query)
        messages.error(request, "Some marks could not be saved. Check the errors below.")
    else:
        form = MarkGridForm(
            students=students, exam_subjects=exam_subjects, existing=existing
        )

    context.update(
        {
            "form": form,
            "students": students,
            "exam_subjects": exam_subjects,
            "publication": _get_publication(exam, classroom, section, create=False),
        }
    )
    return render(request, "results/mark_entry.html", context)


@transaction.atomic
def _save_marks(request, form, students, exam_subjects, existing) -> int:
    saved = 0
    for student in students:
        for exam_subject in exam_subjects:
            value = form.cleaned_data.get(f"mark_{student.id}_{exam_subject.id}")
            absent = form.cleaned_data.get(f"absent_{student.id}_{exam_subject.id}")
            mark = existing.get((student.id, exam_subject.id))
            if value is None and not absent:
                if mark:
                    mark.delete()
                continue
            Mark.objects.update_or_create(
                student=student,
                exam_subject=exam_subject,
                defaults={
                    "obtained_mark": None if absent else value,
                    "is_absent": bool(absent),
                    "updated_by": request.user,
                },
            )
            saved += 1
    return saved


def _get_publication(exam, classroom, section, create=True):
    if not (exam and classroom):
        return None
    lookup = {"exam": exam, "classroom": classroom, "section": section}
    if create:
        publication, _ = ResultPublication.objects.get_or_create(**lookup)
        return publication
    return ResultPublication.objects.filter(**lookup).first()


@login_required
def review(request):
    exam, classroom, section = _selection(request)
    settings_obj = SiteSetting.load()
    context = {
        "select_form": MarkEntrySelectForm(
            initial={"exam": exam, "classroom": classroom, "section": section}
        ),
        "exam": exam,
        "classroom": classroom,
        "section": section,
    }
    if exam and classroom:
        sheets = class_result_sheets(exam, classroom, section, settings_obj)
        sheets_with_marks = [s for s in sheets if s.has_marks]
        exam_subjects = ExamSubject.objects.filter(
            exam=exam, classroom=classroom
        ).select_related("subject")
        highest_rows = []
        for exam_subject in exam_subjects:
            top, holders = highest_mark_holders(
                exam_subject, section if settings_obj.section_wise_highest else None
            )
            highest_rows.append(
                {"subject": exam_subject.subject.name, "top": top, "holders": holders}
            )
        totals = [s.total_obtained for s in sheets_with_marks]
        context.update(
            {
                "sheets": sorted(
                    sheets, key=lambda s: s.total_obtained, reverse=True
                ),
                "highest_rows": highest_rows,
                "publication": _get_publication(exam, classroom, section, create=False),
                "passed_count": sum(1 for s in sheets_with_marks if s.passed),
                "failed_count": sum(1 for s in sheets_with_marks if not s.passed),
                "class_average": (sum(totals) / len(totals)) if totals else None,
                "highest_total": max(totals) if totals else None,
                "incomplete": [s for s in sheets if not s.has_marks],
            }
        )
    return render(request, "results/review.html", context)


@login_required
@require_POST
def toggle_publish(request):
    exam, classroom, section = _selection(request)
    if not (exam and classroom):
        messages.error(request, "Select an exam and a class first.")
        return redirect("results:review")

    publication = _get_publication(exam, classroom, section, create=True)
    publish = request.POST.get("action") == "publish"

    if publish and exam.status != Exam.Status.PUBLISHED:
        exam.status = Exam.Status.PUBLISHED
        exam.save(update_fields=["status"])

    publication.is_published = publish
    publication.published_at = timezone.now() if publish else None
    publication.published_by = request.user if publish else None
    publication.save()

    messages.success(
        request,
        f"Result {'published' if publish else 'unpublished'} for {classroom.name}"
        f"{f' section {section.name}' if section else ''} - {exam}.",
    )
    query = f"?exam={exam.id}&classroom={classroom.id}"
    if section:
        query += f"&section={section.id}"
    return redirect(reverse("results:review") + query)


@login_required
def published_list(request):
    publications = (
        ResultPublication.objects.select_related("exam", "classroom", "section")
        .order_by("-is_published", "-published_at")
    )
    return render(
        request, "results/published.html", {"publications": publications}
    )
