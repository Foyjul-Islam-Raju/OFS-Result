from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from academics.models import ClassRoom, Exam, ExamSubject, Subject
from results.models import Mark, ResultPublication
from results.services import class_result_sheets
from students.models import Student

from .forms import SiteSettingForm
from .models import SiteSetting


@login_required
def home(request):
    settings_obj = SiteSetting.load()
    publications = ResultPublication.objects.select_related("exam", "classroom", "section")

    context = {
        "total_students": Student.objects.active().count(),
        "total_classes": ClassRoom.objects.filter(is_active=True).count(),
        "total_subjects": Subject.objects.filter(is_active=True).count(),
        "total_exams": Exam.objects.count(),
        "published_count": publications.filter(is_published=True).count(),
        "draft_count": publications.filter(is_published=False).count()
        + Exam.objects.filter(status=Exam.Status.DRAFT).count(),
        "recent_publications": publications.order_by("-published_at")[:6],
        "class_rows": ClassRoom.objects.annotate(
            student_count=Count("students", filter=Q(students__is_active=True))
        ),
        "exams": Exam.objects.all()[:10],
    }

    # Optional drill-down statistics for one exam + class.
    exam_id = request.GET.get("exam")
    class_id = request.GET.get("classroom")
    exam = Exam.objects.filter(pk=exam_id).first() if exam_id else None
    classroom = ClassRoom.objects.filter(pk=class_id).first() if class_id else None
    if exam and classroom:
        sheets = [s for s in class_result_sheets(exam, classroom, None, settings_obj) if s.has_marks]
        totals = [s.total_obtained for s in sheets]
        context.update(
            {
                "stat_exam": exam,
                "stat_class": classroom,
                "stat_passed": sum(1 for s in sheets if s.passed),
                "stat_failed": sum(1 for s in sheets if not s.passed),
                "stat_average": (sum(totals) / len(totals)) if totals else None,
                "stat_highest_total": max(totals) if totals else None,
                "stat_count": len(sheets),
                "grade_spread": _grade_spread(sheets),
            }
        )
    context["all_exams"] = Exam.objects.all()
    context["all_classes"] = ClassRoom.objects.all()
    context["selected_exam"] = exam_id or ""
    context["selected_class"] = class_id or ""
    return render(request, "dashboard/home.html", context)


# Percentage bands, not letter grades: these work for regular class exams and
# semester exams alike.
PERCENTAGE_BANDS = [
    ("80% and above", 80),
    ("70 – 79%", 70),
    ("60 – 69%", 60),
    ("50 – 59%", 50),
    ("40 – 49%", 40),
    ("33 – 39%", 33),
    ("Below 33%", 0),
]


def _grade_spread(sheets):
    counts = {label: 0 for label, _ in PERCENTAGE_BANDS}
    for sheet in sheets:
        for label, floor in PERCENTAGE_BANDS:
            if sheet.percentage >= floor:
                counts[label] += 1
                break
    total = max(len(sheets), 1)
    return [
        {"band": label, "count": counts[label], "pct": round(counts[label] * 100 / total)}
        for label, _ in PERCENTAGE_BANDS
    ]


@login_required
def site_settings_view(request):
    instance = SiteSetting.load()
    form = SiteSettingForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Settings saved.")
        return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html", {"form": form})


def error_404(request, exception=None):
    return render(request, "partials/404.html", status=404)


def error_500(request):
    return render(request, "partials/500.html", status=500)
