from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    path("classes/", views.ClassListView.as_view(), name="class_list"),
    path("classes/add/", views.ClassCreateView.as_view(), name="class_add"),
    path("classes/<int:pk>/edit/", views.ClassUpdateView.as_view(), name="class_edit"),
    path("classes/<int:pk>/delete/", views.ClassDeleteView.as_view(), name="class_delete"),

    path("sections/", views.SectionListView.as_view(), name="section_list"),
    path("sections/add/", views.SectionCreateView.as_view(), name="section_add"),
    path("sections/<int:pk>/edit/", views.SectionUpdateView.as_view(), name="section_edit"),
    path("sections/<int:pk>/delete/", views.SectionDeleteView.as_view(), name="section_delete"),

    path("subjects/", views.SubjectListView.as_view(), name="subject_list"),
    path("subjects/add/", views.SubjectCreateView.as_view(), name="subject_add"),
    path("subjects/<int:pk>/edit/", views.SubjectUpdateView.as_view(), name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.SubjectDeleteView.as_view(), name="subject_delete"),

    path("exams/", views.ExamListView.as_view(), name="exam_list"),
    path("exams/add/", views.ExamCreateView.as_view(), name="exam_add"),
    path("exams/<int:pk>/edit/", views.ExamUpdateView.as_view(), name="exam_edit"),
    path("exams/<int:pk>/delete/", views.ExamDeleteView.as_view(), name="exam_delete"),

    path("exam-subjects/", views.ExamSubjectListView.as_view(), name="examsubject_list"),
    path("exam-subjects/add/", views.ExamSubjectCreateView.as_view(), name="examsubject_add"),
    path("exam-subjects/<int:pk>/edit/", views.ExamSubjectUpdateView.as_view(), name="examsubject_edit"),
    path("exam-subjects/<int:pk>/delete/", views.ExamSubjectDeleteView.as_view(), name="examsubject_delete"),

    path("class-subjects/", views.ClassSubjectListView.as_view(), name="classsubject_list"),
    path("class-subjects/add/", views.ClassSubjectCreateView.as_view(), name="classsubject_add"),
    path("class-subjects/bulk/", views.classsubject_bulk, name="classsubject_bulk"),
    path("class-subjects/<int:pk>/edit/", views.ClassSubjectUpdateView.as_view(), name="classsubject_edit"),
    path("class-subjects/<int:pk>/delete/", views.ClassSubjectDeleteView.as_view(), name="classsubject_delete"),

    path("exam-types/", views.ExamTypeListView.as_view(), name="examtype_list"),
    path("exam-types/add/", views.ExamTypeCreateView.as_view(), name="examtype_add"),
    path("exam-types/<int:pk>/edit/", views.ExamTypeUpdateView.as_view(), name="examtype_edit"),
    path("exam-types/<int:pk>/delete/", views.ExamTypeDeleteView.as_view(), name="examtype_delete"),

    path("semesters/", views.SemesterListView.as_view(), name="semester_list"),
    path("semesters/add/", views.SemesterCreateView.as_view(), name="semester_add"),
    path("semesters/<int:pk>/edit/", views.SemesterUpdateView.as_view(), name="semester_edit"),
    path("semesters/<int:pk>/delete/", views.SemesterDeleteView.as_view(), name="semester_delete"),

    path("exam-setup/", views.exam_setup, name="exam_setup"),
]
