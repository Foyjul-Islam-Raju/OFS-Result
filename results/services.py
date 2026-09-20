"""Result building services.

Every screen (student portal, admin review, dashboard, print) goes through
these functions, so the numbers can never disagree between pages.

The shape of a result is decided by the exam's type:

* regular class exam  -> subject marks, total, percentage, pass/fail
* semester exam       -> the same, plus semester GPA and cumulative CGPA
"""
from dataclasses import dataclass, field
from decimal import Decimal

from django.db.models import Max, Q

from academics.models import Exam, ExamSubject
from dashboard.models import SiteSetting
from students.models import Student

from .grading import (
    ABSENT_LABEL,
    calculate_gpa,
    calculate_percentage,
    grade_for_marks,
    grade_for_percentage,
    is_subject_passed,
    point_for_marks,
    to_decimal,
)
from .models import Mark, ResultPublication


def normalise(value) -> str:
    """Render 82.00 as `82` and 82.50 as `82.5`."""
    dec = to_decimal(value).normalize()
    if dec == dec.to_integral_value():
        dec = dec.quantize(Decimal("1"))
    return f"{dec}"


@dataclass
class SubjectRow:
    subject_name: str
    full_mark: int
    obtained: Decimal | None
    is_absent: bool
    percentage: Decimal
    highest_mark: Decimal | None
    passed: bool
    has_mark: bool
    credit: Decimal = Decimal("1")
    grade: str = ""          # filled in only when the exam type asks for it
    grade_point: Decimal = Decimal("0")

    @property
    def obtained_display(self) -> str:
        if self.is_absent:
            return ABSENT_LABEL
        if self.obtained is None:
            return "-"
        return normalise(self.obtained)

    @property
    def highest_display(self) -> str:
        if self.highest_mark is None:
            return "-"
        return normalise(self.highest_mark)


@dataclass
class ResultSheet:
    student: Student
    exam: Exam
    rows: list[SubjectRow] = field(default_factory=list)
    total_full: Decimal = Decimal("0")
    total_obtained: Decimal = Decimal("0")
    percentage: Decimal = Decimal("0")
    passed: bool = False
    failed_subjects: list[str] = field(default_factory=list)
    position: int | None = None
    position_of: int | None = None
    has_marks: bool = False
    subject_count: int = 0
    # Semester-only fields. Left at None for regular exams.
    is_semester: bool = False
    show_letter_grade: bool = False
    grade: str = ""
    gpa: Decimal | None = None
    cgpa: Decimal | None = None
    semesters_counted: int = 0

    @property
    def status_label(self) -> str:
        return "PASSED" if self.passed else "FAILED"

    @property
    def total_obtained_display(self) -> str:
        return normalise(self.total_obtained)

    @property
    def total_full_display(self) -> str:
        return normalise(self.total_full)

    @property
    def average_mark(self) -> Decimal:
        """Average mark per subject, handy alongside the percentage."""
        if not self.subject_count:
            return Decimal("0.00")
        return (self.total_obtained / self.subject_count).quantize(Decimal("0.01"))


def get_exam_subjects(exam: Exam, classroom) -> list[ExamSubject]:
    """Only the subjects this exam was actually conducted in, for this class.

    However many that is — six, ten, or any other number.
    """
    return list(
        ExamSubject.objects.filter(exam=exam, classroom=classroom).select_related("subject")
    )


def pass_percentage_for(exam: Exam, settings_obj: SiteSetting) -> Decimal:
    """Per-exam passing criteria wins; otherwise the school-wide setting."""
    if exam.pass_percentage is not None:
        return to_decimal(exam.pass_percentage)
    return to_decimal(settings_obj.pass_percentage)


def highest_marks_map(exam: Exam, classroom, section=None) -> dict[int, Decimal]:
    """Highest obtained mark per ExamSubject id.

    Scoped strictly to the given exam + class (+ section when section-wise mode
    is enabled), so one class, exam, section or subject can never leak into
    another. Absent students are excluded.
    """
    queryset = Mark.objects.filter(
        exam_subject__exam=exam,
        exam_subject__classroom=classroom,
        is_absent=False,
        obtained_mark__isnull=False,
        student__is_active=True,
        student__classroom=classroom,
    )
    if section is not None:
        queryset = queryset.filter(student__section=section)
    rows = queryset.values("exam_subject").annotate(top=Max("obtained_mark"))
    return {row["exam_subject"]: row["top"] for row in rows}


def highest_mark_holders(exam_subject: ExamSubject, section=None):
    """Students who achieved the highest mark in one exam subject."""
    queryset = Mark.objects.filter(
        exam_subject=exam_subject,
        is_absent=False,
        obtained_mark__isnull=False,
        student__is_active=True,
    ).select_related("student")
    if section is not None:
        queryset = queryset.filter(student__section=section)
    top = queryset.aggregate(top=Max("obtained_mark"))["top"]
    if top is None:
        return top, []
    return top, [mark.student for mark in queryset.filter(obtained_mark=top)]


def _scope_section(student: Student, settings_obj: SiteSetting):
    return student.section if settings_obj.section_wise_highest else None


def build_result(
    student: Student,
    exam: Exam,
    settings_obj: SiteSetting | None = None,
    exam_subjects: list[ExamSubject] | None = None,
    highest_map: dict[int, Decimal] | None = None,
    marks_map: dict[int, Mark] | None = None,
    with_position: bool = True,
    with_cgpa: bool = True,
) -> ResultSheet:
    """Builds the full result sheet for one student in one exam."""
    settings_obj = settings_obj or SiteSetting.load()
    classroom = student.classroom
    if exam_subjects is None:
        exam_subjects = get_exam_subjects(exam, classroom)
    if highest_map is None:
        highest_map = highest_marks_map(
            exam, classroom, _scope_section(student, settings_obj)
        )
    if marks_map is None:
        marks_map = {
            mark.exam_subject_id: mark
            for mark in Mark.objects.filter(
                student=student, exam_subject__in=exam_subjects
            )
        }

    pass_pct = pass_percentage_for(exam, settings_obj)
    sheet = ResultSheet(
        student=student,
        exam=exam,
        is_semester=exam.is_semester,
        show_letter_grade=exam.shows_letter_grade or exam.is_semester,
    )

    for exam_subject in exam_subjects:
        mark = marks_map.get(exam_subject.id)
        has_mark = mark is not None
        is_absent = bool(mark and mark.is_absent)
        obtained = None if (not has_mark or is_absent) else mark.obtained_mark
        percentage = (
            calculate_percentage(obtained, exam_subject.full_mark)
            if obtained is not None
            else Decimal("0.00")
        )
        passed = (
            is_subject_passed(
                obtained,
                exam_subject.full_mark,
                is_absent,
                pass_pct,
                exam_subject.pass_mark,
            )
            if has_mark
            else False
        )
        row = SubjectRow(
            subject_name=exam_subject.subject.name,
            full_mark=exam_subject.full_mark,
            obtained=obtained,
            is_absent=is_absent,
            percentage=percentage,
            highest_mark=highest_map.get(exam_subject.id),
            passed=passed,
            has_mark=has_mark,
            credit=exam_subject.credit,
        )
        if sheet.show_letter_grade and has_mark:
            row.grade = grade_for_marks(obtained, exam_subject.full_mark, is_absent)
            row.grade_point = point_for_marks(obtained, exam_subject.full_mark, is_absent)
        sheet.rows.append(row)

        if has_mark:
            sheet.has_marks = True
            sheet.subject_count += 1
            sheet.total_full += to_decimal(exam_subject.full_mark)
            sheet.total_obtained += to_decimal(obtained or 0)
            if not passed:
                if is_absent and not settings_obj.absent_counts_as_fail:
                    pass
                else:
                    sheet.failed_subjects.append(exam_subject.subject.name)

    sheet.percentage = calculate_percentage(sheet.total_obtained, sheet.total_full)
    sheet.passed = _determine_pass(sheet, pass_pct, settings_obj)

    if sheet.show_letter_grade and sheet.has_marks:
        sheet.grade = "F" if not sheet.passed else grade_for_percentage(sheet.percentage)

    if sheet.is_semester and sheet.has_marks:
        sheet.gpa = calculate_gpa(
            [(row.grade_point, row.credit) for row in sheet.rows if row.has_mark],
            any_subject_failed=bool(sheet.failed_subjects),
            fail_zeroes=settings_obj.fail_zeroes_gpa,
        )
        if with_cgpa:
            sheet.cgpa, sheet.semesters_counted = calculate_cgpa(
                student, exam, settings_obj
            )

    if with_position and settings_obj.show_position and sheet.has_marks:
        sheet.position, sheet.position_of = calculate_position(
            student, exam, settings_obj
        )
    return sheet


def _determine_pass(sheet: ResultSheet, pass_pct: Decimal, settings_obj: SiteSetting) -> bool:
    if not sheet.has_marks:
        return False
    if settings_obj.require_pass_in_every_subject and sheet.failed_subjects:
        return False
    return sheet.percentage >= pass_pct


def calculate_cgpa(student: Student, upto_exam: Exam, settings_obj: SiteSetting):
    """Cumulative GPA across every semester exam this student has sat, up to and
    including the one being viewed.

    Credit-weighted across all subjects of all those semesters, which keeps the
    result correct even when semesters have different subject counts.
    """
    semester_exams = (
        Exam.objects.filter(
            exam_type__uses_cgpa=True,
            exam_subjects__classroom=student.classroom,
            exam_subjects__marks__student=student,
        )
        .distinct()
        .order_by("academic_year", "semester__display_order", "id")
    )
    entries: list[tuple[Decimal, Decimal]] = []
    any_failed = False
    counted = 0
    for exam in semester_exams:
        if (exam.academic_year, exam.id) > (upto_exam.academic_year, upto_exam.id) and exam.id != upto_exam.id:
            continue
        sheet = build_result(
            student,
            exam,
            settings_obj=settings_obj,
            with_position=False,
            with_cgpa=False,
        )
        if not sheet.has_marks:
            continue
        counted += 1
        any_failed = any_failed or bool(sheet.failed_subjects)
        entries.extend(
            (row.grade_point, row.credit) for row in sheet.rows if row.has_mark
        )
    if not entries:
        return None, 0
    return (
        calculate_gpa(
            entries, any_subject_failed=any_failed, fail_zeroes=settings_obj.fail_zeroes_gpa
        ),
        counted,
    )


def class_result_sheets(
    exam: Exam, classroom, section=None, settings_obj: SiteSetting | None = None
) -> list[ResultSheet]:
    """Result sheets for a whole class, in few queries. Used by the review
    screen, dashboard statistics and position calculation."""
    settings_obj = settings_obj or SiteSetting.load()
    exam_subjects = get_exam_subjects(exam, classroom)
    students = list(
        Student.objects.active()
        .filter(classroom=classroom)
        .select_related("classroom", "section")
    )
    if section is not None:
        students = [s for s in students if s.section_id == section.id]

    all_marks = Mark.objects.filter(
        exam_subject__in=exam_subjects, student__in=students
    ).select_related("exam_subject")
    marks_by_student: dict[int, dict[int, Mark]] = {}
    for mark in all_marks:
        marks_by_student.setdefault(mark.student_id, {})[mark.exam_subject_id] = mark

    if settings_obj.section_wise_highest:
        highest_cache: dict[int | None, dict[int, Decimal]] = {}
    else:
        shared_highest = highest_marks_map(exam, classroom, None)

    sheets = []
    for student in students:
        if settings_obj.section_wise_highest:
            key = student.section_id
            if key not in highest_cache:
                highest_cache[key] = highest_marks_map(exam, classroom, student.section)
            highest = highest_cache[key]
        else:
            highest = shared_highest
        sheets.append(
            build_result(
                student,
                exam,
                settings_obj=settings_obj,
                exam_subjects=exam_subjects,
                highest_map=highest,
                marks_map=marks_by_student.get(student.id, {}),
                with_position=False,
                with_cgpa=False,
            )
        )
    return sheets


def calculate_position(student: Student, exam: Exam, settings_obj: SiteSetting):
    """Dense ranking on total obtained marks; equal totals share a position."""
    section = _scope_section(student, settings_obj)
    sheets = [
        sheet
        for sheet in class_result_sheets(exam, student.classroom, section, settings_obj)
        if sheet.has_marks
    ]
    if not sheets:
        return None, None
    totals = sorted({sheet.total_obtained for sheet in sheets}, reverse=True)
    mine = next((s for s in sheets if s.student.id == student.id), None)
    if mine is None:
        return None, None
    return totals.index(mine.total_obtained) + 1, len(sheets)


def is_result_visible(exam: Exam, classroom, section=None) -> bool:
    """Server-side gate: both the exam and the class publication must be live."""
    if exam.status != Exam.Status.PUBLISHED:
        return False
    publications = ResultPublication.objects.filter(
        exam=exam, classroom=classroom, is_published=True
    )
    if section is not None:
        return publications.filter(Q(section=section) | Q(section__isnull=True)).exists()
    return publications.filter(section__isnull=True).exists()


def published_exams_for_student(student: Student) -> list[Exam]:
    """Only exams published for this student's own class/section that actually
    contain marks for this student."""
    candidates = (
        Exam.objects.filter(
            status=Exam.Status.PUBLISHED,
            publications__classroom=student.classroom,
            publications__is_published=True,
        )
        .filter(
            Q(publications__section__isnull=True)
            | Q(publications__section=student.section)
        )
        .select_related("exam_type", "semester")
        .distinct()
    )
    exams_with_marks = set(
        Mark.objects.filter(
            student=student, exam_subject__exam__in=candidates
        ).values_list("exam_subject__exam_id", flat=True)
    )
    return [exam for exam in candidates if exam.id in exams_with_marks]
