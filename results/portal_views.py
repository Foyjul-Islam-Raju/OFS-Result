"""Student-facing views.

Security model
--------------
A student proves who they are by submitting Student ID + Class together. That
pair is verified server-side and the verified student's primary key is stored in
the session. Every later page reads the student from the session, never from the
URL, so editing a URL cannot reveal somebody else's result. Publication state is
re-checked on every request.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from academics.models import Exam
from dashboard.models import SiteSetting
from students.models import Student

from .forms import StudentLookupForm
from .services import build_result, is_result_visible, published_exams_for_student

SESSION_KEY = "verified_student_pk"


def _verified_student(request) -> Student | None:
    pk = request.session.get(SESSION_KEY)
    if not pk:
        return None
    return (
        Student.objects.filter(pk=pk, is_active=True)
        .select_related("classroom", "section")
        .first()
    )


def lookup(request):
    """Landing page: Student ID + Class."""
    form = StudentLookupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student_id = form.cleaned_data["student_id"]
        classroom = form.cleaned_data["classroom"]
        student = (
            Student.objects.select_related("classroom", "section")
            .filter(student_id__iexact=student_id, is_active=True)
            .first()
        )
        if student is None:
            form.add_error("student_id", "Student ID not found.")
        elif student.classroom_id != classroom.id:
            form.add_error(
                "classroom", "The selected class does not match this Student ID."
            )
        else:
            request.session[SESSION_KEY] = student.pk
            request.session.set_expiry(60 * 60)
            return redirect("portal:exam_list")
        if form.errors:
            messages.error(request, "Invalid Student ID or Class.")
    return render(request, "portal/lookup.html", {"form": form})


def exam_list(request):
    student = _verified_student(request)
    if student is None:
        return redirect("portal:lookup")
    exams = published_exams_for_student(student)
    return render(
        request, "portal/exam_list.html", {"student": student, "exams": exams}
    )


def _result_context(request, exam_id):
    student = _verified_student(request)
    if student is None:
        return None, None, redirect("portal:lookup")

    exam = get_object_or_404(Exam, pk=exam_id)
    if not is_result_visible(exam, student.classroom, student.section):
        messages.warning(request, "This result has not been published yet.")
        return None, None, redirect("portal:exam_list")

    sheet = build_result(student, exam, settings_obj=SiteSetting.load())
    if not sheet.has_marks:
        messages.warning(request, "No result is available for this examination.")
        return None, None, redirect("portal:exam_list")
    return student, sheet, None


def result_detail(request, exam_id: int):
    student, sheet, redirect_response = _result_context(request, exam_id)
    if redirect_response:
        return redirect_response
    return render(
        request,
        "portal/result.html",
        {"student": student, "sheet": sheet, "exam": sheet.exam},
    )


def result_print(request, exam_id: int):
    student, sheet, redirect_response = _result_context(request, exam_id)
    if redirect_response:
        return redirect_response
    return render(
        request,
        "portal/result_print.html",
        {"student": student, "sheet": sheet, "exam": sheet.exam},
    )


def sign_out(request):
    request.session.pop(SESSION_KEY, None)
    return redirect("portal:lookup")
