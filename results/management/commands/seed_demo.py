"""Creates a realistic demo dataset that exercises the dynamic subject system.

* Class 6  — 6 subjects, regular class exams (marks, total, percentage, pass/fail)
* Class 9  — 10 subjects, regular class exams
* Class 10 — semester examinations, so GPA and CGPA appear

Safe to run repeatedly: everything is fetched or created, never duplicated.

    python manage.py seed_demo
"""
import random
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

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
from results.models import Mark, ResultPublication
from students.models import Student

CLASSES = [
    "Play Group", "Nursery", "Class 1", "Class 2", "Class 3", "Class 4",
    "Class 5", "Class 6", "Class 7", "Class 8", "Class 9", "Class 10",
]

# The full school subject catalogue. Individual classes study a subset.
SUBJECTS = [
    ("Bangla", "BAN"), ("English", "ENG"), ("Mathematics", "MAT"),
    ("Science", "SCI"), ("ICT", "ICT"), ("Religion", "REL"),
    ("Physics", "PHY"), ("Chemistry", "CHE"), ("Biology", "BIO"),
    ("Higher Mathematics", "HMT"), ("Optional Subject", "OPT"),
]

# Exactly the example from the requirements: 6 subjects vs 10 subjects.
CURRICULUM = {
    "Class 6": ["Bangla", "English", "Mathematics", "Science", "ICT", "Religion"],
    "Class 9": [
        "Bangla", "English", "Mathematics", "Physics", "Chemistry", "Biology",
        "ICT", "Religion", "Higher Mathematics", "Optional Subject",
    ],
    "Class 10": [
        "Bangla", "English", "Mathematics", "Physics", "Chemistry", "ICT",
    ],
}

NAMES = [
    "Rahim Ahmed", "Karim Hossain", "Nusrat Jahan", "Sumaiya Akter", "Foyjul Islam",
    "Tanvir Rahman", "Mehedi Hasan", "Sadia Islam", "Arif Chowdhury", "Jannatul Ferdous",
    "Shakib Al Amin", "Rumana Parvin", "Imran Kabir", "Nabila Sultana", "Rafiul Haque",
    "Tasnim Ara", "Sabbir Ahmed", "Maliha Noor", "Hasibur Rahman", "Farhana Yasmin",
]


class Command(BaseCommand):
    help = "Seeds classes, curricula, exam types, exams, students and marks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-marks", action="store_true",
            help="Delete existing marks before generating new ones.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(20260101)  # deterministic demo data

        settings_obj = SiteSetting.load()
        settings_obj.institution_name = "Online Foundation School"
        settings_obj.institution_tagline = "Result Portal"
        settings_obj.address = "Dhaka, Bangladesh"
        settings_obj.show_position = True
        settings_obj.save()

        classes = {}
        for index, name in enumerate(CLASSES, start=1):
            classroom, _ = ClassRoom.objects.get_or_create(
                name=name, defaults={"display_order": index}
            )
            classes[name] = classroom

        for name in ("Class 6", "Class 9"):
            for section_name in ("A", "B"):
                Section.objects.get_or_create(classroom=classes[name], name=section_name)

        subjects = {}
        for index, (name, code) in enumerate(SUBJECTS, start=1):
            subject, _ = Subject.objects.get_or_create(
                name=name, defaults={"code": code, "display_order": index}
            )
            subjects[name] = subject

        # Curriculum: this is what makes the subject count per class dynamic.
        for class_name, subject_names in CURRICULUM.items():
            for order, subject_name in enumerate(subject_names, start=1):
                ClassSubject.objects.get_or_create(
                    classroom=classes[class_name],
                    subject=subjects[subject_name],
                    defaults={
                        # ICT out of 80 so different full marks are visible.
                        "default_full_mark": 80 if subject_name == "ICT" else 100,
                        "display_order": order,
                        "is_optional": subject_name == "Optional Subject",
                        "credit": Decimal("1"),
                    },
                )

        regular_type, _ = ExamType.objects.get_or_create(
            name="Class Examination",
            defaults={"uses_cgpa": False, "show_letter_grade": False},
        )
        semester_type, _ = ExamType.objects.get_or_create(
            name="Semester Examination",
            defaults={"uses_cgpa": True, "show_letter_grade": True},
        )

        sem1, _ = Semester.objects.get_or_create(
            name="Semester 1", academic_year=2026, defaults={"display_order": 1}
        )
        sem2, _ = Semester.objects.get_or_create(
            name="Semester 2", academic_year=2026, defaults={"display_order": 2}
        )

        exams = {}
        for name, exam_type, semester in [
            ("1st Tutorial Examination", regular_type, None),
            ("2nd Tutorial Examination", regular_type, None),
            ("Half Yearly Examination", regular_type, None),
            ("Semester 1 Final Examination", semester_type, sem1),
            ("Semester 2 Final Examination", semester_type, sem2),
        ]:
            exam, _ = Exam.objects.get_or_create(
                name=name,
                academic_year=2026,
                defaults={"exam_type": exam_type, "semester": semester},
            )
            if exam.exam_type_id is None:
                exam.exam_type = exam_type
                exam.semester = semester
                exam.save(update_fields=["exam_type", "semester"])
            exams[name] = exam

        # Which subjects each exam was conducted in. The tutorial exams skip
        # Religion in Class 6, to prove only examined subjects show up.
        plan = [
            ("1st Tutorial Examination", "Class 6", lambda s: s != "Religion"),
            ("2nd Tutorial Examination", "Class 6", lambda s: True),
            ("Half Yearly Examination", "Class 6", lambda s: True),
            ("1st Tutorial Examination", "Class 9", lambda s: True),
            ("2nd Tutorial Examination", "Class 9", lambda s: True),
            ("Semester 1 Final Examination", "Class 10", lambda s: True),
            ("Semester 2 Final Examination", "Class 10", lambda s: True),
        ]
        for exam_name, class_name, keep in plan:
            exam = exams[exam_name]
            classroom = classes[class_name]
            for class_subject in ClassSubject.objects.filter(classroom=classroom):
                if not keep(class_subject.subject.name):
                    continue
                ExamSubject.objects.get_or_create(
                    exam=exam,
                    classroom=classroom,
                    subject=class_subject.subject,
                    defaults={
                        "full_mark": class_subject.default_full_mark,
                        "credit": class_subject.credit,
                        "display_order": class_subject.display_order,
                    },
                )

        students = self._create_students(classes)

        if options["reset_marks"]:
            Mark.objects.all().delete()

        for exam_name, class_name, _ in plan:
            self._create_marks(exams[exam_name], classes[class_name], students)

        published = [
            ("1st Tutorial Examination", "Class 6"),
            ("2nd Tutorial Examination", "Class 6"),
            ("1st Tutorial Examination", "Class 9"),
            ("2nd Tutorial Examination", "Class 9"),
            ("Semester 1 Final Examination", "Class 10"),
            ("Semester 2 Final Examination", "Class 10"),
        ]
        for exam_name, class_name in published:
            exam = exams[exam_name]
            exam.status = Exam.Status.PUBLISHED
            exam.save(update_fields=["status"])
            ResultPublication.objects.update_or_create(
                exam=exam,
                classroom=classes[class_name],
                section=None,
                defaults={"is_published": True, "published_at": timezone.now()},
            )

        # Left as a draft so you can confirm students cannot see it.
        draft = exams["Half Yearly Examination"]
        draft.status = Exam.Status.DRAFT
        draft.save(update_fields=["status"])

        if not User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING("No superuser yet. Run: python manage.py createsuperuser")
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write(f"  Students: {Student.objects.count()}   Marks: {Mark.objects.count()}")
        self.stdout.write("  Class 6  — 6 subjects, class exams (1st tutorial skips Religion)")
        self.stdout.write("  Class 9  — 10 subjects, class exams")
        self.stdout.write("  Class 10 — semester exams, so GPA and CGPA show")
        self.stdout.write("  Draft (hidden from students): Half Yearly Examination 2026")
        self.stdout.write("")
        self.stdout.write("  Portal: ID 6001 / Class 6 · 9001 / Class 9 · 10001 / Class 10")

    def _create_students(self, classes):
        created = []
        plan = [("Class 6", 6000, 12), ("Class 9", 9000, 10), ("Class 10", 10000, 8)]
        for class_name, base_id, count in plan:
            classroom = classes[class_name]
            sections = list(classroom.sections.order_by("name"))
            for offset in range(1, count + 1):
                section = sections[(offset - 1) % len(sections)] if sections else None
                student, _ = Student.objects.get_or_create(
                    student_id=str(base_id + offset),
                    defaults={
                        "name": NAMES[(offset - 1) % len(NAMES)],
                        "classroom": classroom,
                        "section": section,
                        "roll": offset,
                    },
                )
                created.append(student)
        return created

    def _create_marks(self, exam, classroom, students):
        exam_subjects = list(ExamSubject.objects.filter(exam=exam, classroom=classroom))
        class_students = [s for s in students if s.classroom_id == classroom.id]
        for student in class_students:
            for exam_subject in exam_subjects:
                # One deliberate absence so the Absent path is visible.
                absent = student.roll == 4 and exam_subject.subject.name == "ICT"
                if absent:
                    value = None
                else:
                    ceiling = exam_subject.full_mark
                    value = Decimal(random.randint(int(ceiling * 0.40), ceiling))
                Mark.objects.update_or_create(
                    student=student,
                    exam_subject=exam_subject,
                    defaults={"obtained_mark": value, "is_absent": absent},
                )
