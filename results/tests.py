"""Tests covering every rule listed in the project requirements."""
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from academics.models import (
    ClassRoom,
    ClassSubject,
    Exam,
    ExamSubject,
    ExamType,
    Section,
    Semester,
    Subject,
)
from dashboard.models import SiteSetting
from students.models import Student

from .forms import MarkGridForm
from .grading import (
    calculate_gpa,
    calculate_percentage,
    grade_for_marks,
    grade_for_percentage,
)
from .models import Mark, ResultPublication
from .services import build_result, highest_marks_map, is_result_visible


class BaseData(TestCase):
    """Small but complete fixture: two classes, two exams, five subjects."""

    @classmethod
    def setUpTestData(cls):
        cls.settings_obj = SiteSetting.load()
        cls.class6 = ClassRoom.objects.create(name="Class 6", display_order=6)
        cls.class7 = ClassRoom.objects.create(name="Class 7", display_order=7)
        cls.section_a = Section.objects.create(classroom=cls.class6, name="A")
        cls.section_b = Section.objects.create(classroom=cls.class6, name="B")

        cls.bangla = Subject.objects.create(name="Bangla", display_order=1)
        cls.english = Subject.objects.create(name="English", display_order=2)
        cls.maths = Subject.objects.create(name="Mathematics", display_order=3)

        cls.regular_type = ExamType.objects.create(
            name="Class Examination", uses_cgpa=False, show_letter_grade=False
        )
        cls.semester_type = ExamType.objects.create(
            name="Semester Examination", uses_cgpa=True, show_letter_grade=True
        )
        cls.sem1 = Semester.objects.create(name="Semester 1", academic_year=2026, display_order=1)

        cls.exam1 = Exam.objects.create(
            name="1st Tutorial Examination", academic_year=2026, exam_type=cls.regular_type
        )
        cls.exam2 = Exam.objects.create(
            name="2nd Tutorial Examination", academic_year=2026, exam_type=cls.regular_type
        )
        cls.semester_exam = Exam.objects.create(
            name="Semester 1 Final Examination",
            academic_year=2026,
            exam_type=cls.semester_type,
            semester=cls.sem1,
        )

        cls.es6_bangla = ExamSubject.objects.create(
            exam=cls.exam1, classroom=cls.class6, subject=cls.bangla, full_mark=100
        )
        cls.es6_english = ExamSubject.objects.create(
            exam=cls.exam1, classroom=cls.class6, subject=cls.english, full_mark=100
        )
        cls.es6_maths = ExamSubject.objects.create(
            exam=cls.exam1, classroom=cls.class6, subject=cls.maths, full_mark=80
        )
        cls.es7_maths = ExamSubject.objects.create(
            exam=cls.exam1, classroom=cls.class7, subject=cls.maths, full_mark=100
        )
        cls.es6_maths_exam2 = ExamSubject.objects.create(
            exam=cls.exam2, classroom=cls.class6, subject=cls.maths, full_mark=100
        )

        cls.rahim = Student.objects.create(
            student_id="6001", name="Rahim Ahmed", classroom=cls.class6,
            section=cls.section_a, roll=1,
        )
        cls.karim = Student.objects.create(
            student_id="6002", name="Karim Hossain", classroom=cls.class6,
            section=cls.section_b, roll=2,
        )
        cls.tanvir = Student.objects.create(
            student_id="7001", name="Tanvir Rahman", classroom=cls.class7, roll=1,
        )

    def publish(self, exam, classroom):
        exam.status = Exam.Status.PUBLISHED
        exam.save(update_fields=["status"])
        ResultPublication.objects.update_or_create(
            exam=exam, classroom=classroom, section=None,
            defaults={"is_published": True},
        )


class GradingTests(BaseData):
    def test_percentage_calculation(self):
        self.assertEqual(calculate_percentage(64, 80), Decimal("80.00"))
        self.assertEqual(calculate_percentage(437, 500), Decimal("87.40"))
        self.assertEqual(calculate_percentage(0, 100), Decimal("0.00"))

    def test_grade_calculation_uses_percentage_not_raw_marks(self):
        # 64 out of 80 is 80% -> A+, even though 64 out of 100 would be A-.
        self.assertEqual(grade_for_marks(64, 80), "A+")
        self.assertEqual(grade_for_marks(64, 100), "A-")

    def test_every_grade_band(self):
        cases = [
            (100, "A+"), (80, "A+"), (79, "A"), (70, "A"), (69, "A-"), (60, "A-"),
            (59, "B"), (50, "B"), (49, "C"), (40, "C"), (39, "D"), (33, "D"),
            (32, "F"), (0, "F"),
        ]
        for percentage, expected in cases:
            with self.subTest(percentage=percentage):
                self.assertEqual(grade_for_percentage(percentage), expected)

    def test_absent_subject_is_not_treated_as_zero_marks(self):
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_bangla, is_absent=True)
        sheet = build_result(self.rahim, self.exam1)
        row = next(r for r in sheet.rows if r.subject_name == "Bangla")
        self.assertTrue(row.is_absent)
        self.assertFalse(row.passed)
        self.assertEqual(row.obtained_display, "Absent")

    def test_absent_shows_as_absent_on_a_graded_exam(self):
        es = ExamSubject.objects.create(
            exam=self.semester_exam, classroom=self.class6,
            subject=self.bangla, full_mark=100,
        )
        Mark.objects.create(student=self.rahim, exam_subject=es, is_absent=True)
        sheet = build_result(self.rahim, self.semester_exam)
        row = next(r for r in sheet.rows if r.subject_name == "Bangla")
        self.assertEqual(row.grade, "Absent")


class OverallResultTests(BaseData):
    def setUp(self):
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_bangla, obtained_mark=82)
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_english, obtained_mark=76)
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_maths, obtained_mark=64)

    def test_overall_percentage_and_grade(self):
        sheet = build_result(self.rahim, self.exam1)
        self.assertEqual(sheet.total_obtained, Decimal("222"))
        self.assertEqual(sheet.total_full, Decimal("280"))
        self.assertEqual(sheet.percentage, Decimal("79.29"))
        self.assertTrue(sheet.passed)
        self.assertEqual(sheet.status_label, "PASSED")

    def test_failing_one_subject_fails_the_result(self):
        mark = Mark.objects.get(student=self.rahim, exam_subject=self.es6_english)
        mark.obtained_mark = Decimal("10")  # 10% -> below the 33% rule
        mark.save()
        sheet = build_result(self.rahim, self.exam1)
        self.assertFalse(sheet.passed)
        self.assertEqual(sheet.status_label, "FAILED")
        self.assertIn("English", sheet.failed_subjects)

    def test_pass_rule_is_configurable(self):
        settings_obj = SiteSetting.load()
        settings_obj.require_pass_in_every_subject = False
        settings_obj.pass_percentage = Decimal("40")
        settings_obj.save()
        mark = Mark.objects.get(student=self.rahim, exam_subject=self.es6_english)
        mark.obtained_mark = Decimal("10")
        mark.save()
        sheet = build_result(self.rahim, self.exam1, settings_obj=SiteSetting.load())
        self.assertTrue(sheet.passed)  # overall 156/280 = 55.71% >= 40%


class HighestMarkTests(BaseData):
    def setUp(self):
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_maths, obtained_mark=70)
        Mark.objects.create(student=self.karim, exam_subject=self.es6_maths, obtained_mark=78)
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_bangla, obtained_mark=82)
        Mark.objects.create(student=self.karim, exam_subject=self.es6_bangla, obtained_mark=95)

    def test_highest_mark_is_the_class_top_score(self):
        highest = highest_marks_map(self.exam1, self.class6)
        self.assertEqual(highest[self.es6_maths.id], Decimal("78"))
        self.assertEqual(highest[self.es6_bangla.id], Decimal("95"))

    def test_highest_mark_appears_on_the_result_sheet(self):
        sheet = build_result(self.rahim, self.exam1)
        row = next(r for r in sheet.rows if r.subject_name == "Mathematics")
        self.assertEqual(row.highest_mark, Decimal("78"))

    def test_another_class_does_not_affect_highest_mark(self):
        Mark.objects.create(student=self.tanvir, exam_subject=self.es7_maths, obtained_mark=99)
        highest = highest_marks_map(self.exam1, self.class6)
        self.assertEqual(highest[self.es6_maths.id], Decimal("78"))

    def test_another_exam_does_not_affect_highest_mark(self):
        Mark.objects.create(
            student=self.rahim, exam_subject=self.es6_maths_exam2, obtained_mark=100
        )
        highest = highest_marks_map(self.exam1, self.class6)
        self.assertEqual(highest[self.es6_maths.id], Decimal("78"))

    def test_subjects_are_calculated_separately(self):
        highest = highest_marks_map(self.exam1, self.class6)
        self.assertNotEqual(highest[self.es6_maths.id], highest[self.es6_bangla.id])

    def test_section_wise_highest_mark(self):
        settings_obj = SiteSetting.load()
        settings_obj.section_wise_highest = True
        settings_obj.save()
        highest = highest_marks_map(self.exam1, self.class6, section=self.section_a)
        self.assertEqual(highest[self.es6_maths.id], Decimal("70"))  # Rahim only

    def test_absent_students_are_excluded_from_highest_mark(self):
        Mark.objects.filter(student=self.karim, exam_subject=self.es6_maths).update(
            obtained_mark=None, is_absent=True
        )
        highest = highest_marks_map(self.exam1, self.class6)
        self.assertEqual(highest[self.es6_maths.id], Decimal("70"))

    def test_tied_highest_mark_is_reported_once(self):
        Mark.objects.filter(student=self.rahim, exam_subject=self.es6_maths).update(
            obtained_mark=78
        )
        highest = highest_marks_map(self.exam1, self.class6)
        self.assertEqual(highest[self.es6_maths.id], Decimal("78"))


class MarkValidationTests(BaseData):
    def _form(self, value, absent=False):
        data = {
            f"mark_{self.rahim.id}_{self.es6_maths.id}": value,
            f"absent_{self.rahim.id}_{self.es6_maths.id}": "on" if absent else "",
        }
        return MarkGridForm(
            data, students=[self.rahim], exam_subjects=[self.es6_maths]
        )

    def test_mark_above_full_mark_is_rejected(self):
        form = self._form("101")  # full mark is 80
        self.assertFalse(form.is_valid())

    def test_negative_mark_is_rejected(self):
        self.assertFalse(self._form("-5").is_valid())

    def test_non_numeric_mark_is_rejected(self):
        self.assertFalse(self._form("abc").is_valid())

    def test_empty_mark_is_allowed(self):
        self.assertTrue(self._form("").is_valid())

    def test_valid_mark_is_accepted(self):
        self.assertTrue(self._form("64").is_valid())

    def test_absent_with_a_mark_is_rejected(self):
        self.assertFalse(self._form("64", absent=True).is_valid())

    def test_duplicate_mark_for_student_exam_subject_is_prevented(self):
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_maths, obtained_mark=50)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Mark.objects.create(
                    student=self.rahim, exam_subject=self.es6_maths, obtained_mark=60
                )


class StudentPortalTests(BaseData):
    def setUp(self):
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_bangla, obtained_mark=82)
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_maths, obtained_mark=64)
        Mark.objects.create(student=self.karim, exam_subject=self.es6_bangla, obtained_mark=95)

    def _sign_in(self, student_id, classroom):
        return self.client.post(
            reverse("portal:lookup"),
            {"student_id": student_id, "classroom": classroom.id},
            follow=True,
        )

    def test_invalid_student_id_is_rejected(self):
        response = self._sign_in("9999", self.class6)
        self.assertContains(response, "Student ID not found.")

    def test_wrong_class_for_valid_id_is_rejected(self):
        response = self._sign_in("6001", self.class7)
        self.assertContains(response, "does not match this Student ID")

    def test_draft_result_cannot_be_viewed(self):
        self._sign_in("6001", self.class6)
        response = self.client.get(
            reverse("portal:result", args=[self.exam1.id]), follow=True
        )
        self.assertContains(response, "has not been published yet")

    def test_published_result_can_be_viewed(self):
        self.publish(self.exam1, self.class6)
        self._sign_in("6001", self.class6)
        response = self.client.get(reverse("portal:result", args=[self.exam1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rahim Ahmed")
        self.assertContains(response, "82")

    def test_unpublishing_hides_the_result_again(self):
        self.publish(self.exam1, self.class6)
        self._sign_in("6001", self.class6)
        ResultPublication.objects.filter(exam=self.exam1, classroom=self.class6).update(
            is_published=False
        )
        response = self.client.get(
            reverse("portal:result", args=[self.exam1.id]), follow=True
        )
        self.assertContains(response, "has not been published yet")

    def test_student_cannot_reach_another_students_result_by_url(self):
        """The URL only carries an exam id; the student comes from the session."""
        self.publish(self.exam1, self.class6)
        self._sign_in("6001", self.class6)
        response = self.client.get(reverse("portal:result", args=[self.exam1.id]))
        self.assertContains(response, "Rahim Ahmed")
        self.assertNotContains(response, "Karim Hossain")

    def test_result_pages_require_a_verified_session(self):
        self.publish(self.exam1, self.class6)
        response = self.client.get(reverse("portal:result", args=[self.exam1.id]))
        self.assertRedirects(response, reverse("portal:lookup"))

    def test_only_published_exams_are_listed(self):
        self.publish(self.exam1, self.class6)
        self._sign_in("6001", self.class6)
        response = self.client.get(reverse("portal:exam_list"))
        self.assertContains(response, "1st Tutorial Examination")
        self.assertNotContains(response, "2nd Tutorial Examination")

    def test_visibility_helper_requires_both_gates(self):
        self.assertFalse(is_result_visible(self.exam1, self.class6))
        self.publish(self.exam1, self.class6)
        self.assertTrue(is_result_visible(self.exam1, self.class6))
        self.exam1.status = Exam.Status.DRAFT
        self.exam1.save(update_fields=["status"])
        self.assertFalse(is_result_visible(self.exam1, self.class6))

    def test_print_view_renders_for_a_published_result(self):
        self.publish(self.exam1, self.class6)
        self._sign_in("6001", self.class6)
        response = self.client.get(reverse("portal:result_print", args=[self.exam1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report Card")


class AdminAccessTests(BaseData):
    def test_admin_pages_require_login(self):
        for name in [
            "dashboard:home", "students:list", "academics:class_list",
            "results:mark_entry", "results:review",
        ]:
            with self.subTest(view=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login/", response["Location"])


class DynamicSubjectTests(BaseData):
    """Different classes hold different numbers of subjects, with no code change."""

    def setUp(self):
        # Class 6 sits three subjects in exam1; Class 7 sits one.
        for exam_subject, value in [
            (self.es6_bangla, 80), (self.es6_english, 70), (self.es6_maths, 60)
        ]:
            Mark.objects.create(
                student=self.rahim, exam_subject=exam_subject, obtained_mark=value
            )
        Mark.objects.create(
            student=self.tanvir, exam_subject=self.es7_maths, obtained_mark=75
        )

    def test_each_class_shows_only_its_own_subjects(self):
        class6 = build_result(self.rahim, self.exam1)
        class7 = build_result(self.tanvir, self.exam1)
        self.assertEqual(class6.subject_count, 3)
        self.assertEqual(class7.subject_count, 1)
        self.assertEqual(
            [r.subject_name for r in class7.rows if r.has_mark], ["Mathematics"]
        )

    def test_adding_a_subject_later_needs_no_code_change(self):
        religion = Subject.objects.create(name="Religion", display_order=9)
        new_exam_subject = ExamSubject.objects.create(
            exam=self.exam1, classroom=self.class6, subject=religion, full_mark=100
        )
        Mark.objects.create(
            student=self.rahim, exam_subject=new_exam_subject, obtained_mark=90
        )
        sheet = build_result(self.rahim, self.exam1)
        self.assertEqual(sheet.subject_count, 4)
        self.assertIn("Religion", [r.subject_name for r in sheet.rows])

    def test_only_examined_subjects_appear(self):
        """The class curriculum can be larger than what an exam covered."""
        religion = Subject.objects.create(name="Religion", display_order=9)
        ClassSubject.objects.create(
            classroom=self.class6, subject=religion, default_full_mark=100
        )
        sheet = build_result(self.rahim, self.exam1)
        self.assertEqual(ClassSubject.objects.filter(classroom=self.class6).count(), 1)
        self.assertNotIn("Religion", [r.subject_name for r in sheet.rows])

    def test_totals_follow_the_subject_count(self):
        sheet = build_result(self.rahim, self.exam1)
        self.assertEqual(sheet.total_full, Decimal("280"))  # 100 + 100 + 80
        self.assertEqual(sheet.total_obtained, Decimal("210"))


class RegularExamPresentationTests(BaseData):
    """Regular class exams: marks, total, percentage, pass/fail. Nothing else."""

    def setUp(self):
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_bangla, obtained_mark=82)
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_maths, obtained_mark=64)

    def test_no_letter_grade_on_a_regular_exam(self):
        sheet = build_result(self.rahim, self.exam1)
        self.assertFalse(sheet.show_letter_grade)
        self.assertEqual(sheet.grade, "")
        self.assertTrue(all(row.grade == "" for row in sheet.rows))

    def test_no_gpa_on_a_regular_exam(self):
        sheet = build_result(self.rahim, self.exam1)
        self.assertFalse(sheet.is_semester)
        self.assertIsNone(sheet.gpa)
        self.assertIsNone(sheet.cgpa)

    def test_percentage_and_pass_status_are_present(self):
        sheet = build_result(self.rahim, self.exam1)
        self.assertEqual(sheet.percentage, Decimal("81.11"))  # 146/180
        self.assertEqual(sheet.status_label, "PASSED")

    def test_an_exam_with_no_type_is_treated_as_regular(self):
        self.exam1.exam_type = None
        self.exam1.save(update_fields=["exam_type"])
        sheet = build_result(self.rahim, self.exam1)
        self.assertFalse(sheet.is_semester)
        self.assertFalse(sheet.show_letter_grade)


class SemesterExamTests(BaseData):
    """Semester exams add GPA and CGPA on top of everything above."""

    def setUp(self):
        self.sem_bangla = ExamSubject.objects.create(
            exam=self.semester_exam, classroom=self.class6,
            subject=self.bangla, full_mark=100, credit=Decimal("1"),
        )
        self.sem_maths = ExamSubject.objects.create(
            exam=self.semester_exam, classroom=self.class6,
            subject=self.maths, full_mark=100, credit=Decimal("3"),
        )
        Mark.objects.create(student=self.rahim, exam_subject=self.sem_bangla, obtained_mark=85)
        Mark.objects.create(student=self.rahim, exam_subject=self.sem_maths, obtained_mark=72)

    def test_gpa_is_credit_weighted(self):
        sheet = build_result(self.rahim, self.semester_exam)
        self.assertTrue(sheet.is_semester)
        # Bangla 85% -> 5.00 (credit 1), Maths 72% -> 4.00 (credit 3)
        # (5*1 + 4*3) / 4 = 4.25
        self.assertEqual(sheet.gpa, Decimal("4.25"))

    def test_marks_total_and_percentage_still_appear(self):
        sheet = build_result(self.rahim, self.semester_exam)
        self.assertEqual(sheet.total_obtained, Decimal("157"))
        self.assertEqual(sheet.percentage, Decimal("78.50"))
        self.assertEqual(sheet.status_label, "PASSED")

    def test_letter_grades_appear_on_semester_exams(self):
        sheet = build_result(self.rahim, self.semester_exam)
        self.assertTrue(sheet.show_letter_grade)
        self.assertEqual(
            {r.subject_name: r.grade for r in sheet.rows},
            {"Bangla": "A+", "Mathematics": "A"},
        )

    def test_cgpa_covers_one_semester_when_only_one_exists(self):
        sheet = build_result(self.rahim, self.semester_exam)
        self.assertEqual(sheet.cgpa, sheet.gpa)
        self.assertEqual(sheet.semesters_counted, 1)

    def test_cgpa_accumulates_across_semesters(self):
        sem2 = Semester.objects.create(name="Semester 2", academic_year=2026, display_order=2)
        exam2 = Exam.objects.create(
            name="Semester 2 Final Examination", academic_year=2026,
            exam_type=self.semester_type, semester=sem2,
        )
        es = ExamSubject.objects.create(
            exam=exam2, classroom=self.class6, subject=self.english,
            full_mark=100, credit=Decimal("4"),
        )
        Mark.objects.create(student=self.rahim, exam_subject=es, obtained_mark=55)  # B -> 3.00
        sheet = build_result(self.rahim, exam2)
        # (5*1 + 4*3 + 3*4) / 8 = 3.63
        self.assertEqual(sheet.cgpa, Decimal("3.63"))
        self.assertEqual(sheet.semesters_counted, 2)

    def test_failing_a_subject_zeroes_the_gpa(self):
        Mark.objects.filter(student=self.rahim, exam_subject=self.sem_maths).update(
            obtained_mark=Decimal("10")
        )
        sheet = build_result(self.rahim, self.semester_exam)
        self.assertEqual(sheet.gpa, Decimal("0.00"))
        self.assertFalse(sheet.passed)

    def test_gpa_averaging_is_configurable(self):
        settings_obj = SiteSetting.load()
        settings_obj.fail_zeroes_gpa = False
        settings_obj.save()
        Mark.objects.filter(student=self.rahim, exam_subject=self.sem_maths).update(
            obtained_mark=Decimal("10")
        )
        sheet = build_result(self.rahim, self.semester_exam, settings_obj=SiteSetting.load())
        # (5*1 + 0*3) / 4 = 1.25
        self.assertEqual(sheet.gpa, Decimal("1.25"))

    def test_gpa_helper_handles_an_empty_list(self):
        self.assertEqual(calculate_gpa([]), Decimal("0.00"))


class PassingCriteriaTests(BaseData):
    def setUp(self):
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_bangla, obtained_mark=38)
        Mark.objects.create(student=self.rahim, exam_subject=self.es6_maths, obtained_mark=30)

    def test_per_exam_passing_criteria_overrides_the_school_setting(self):
        self.assertTrue(build_result(self.rahim, self.exam1).passed)  # 33% rule
        self.exam1.pass_percentage = Decimal("40")
        self.exam1.save(update_fields=["pass_percentage"])
        self.assertFalse(build_result(self.rahim, self.exam1).passed)
