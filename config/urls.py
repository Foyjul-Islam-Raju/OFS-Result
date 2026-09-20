from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

handler404 = "dashboard.views.error_404"
handler500 = "dashboard.views.error_500"

urlpatterns = [
    path("", include("results.portal_urls")),
    path("manage/", include("dashboard.urls")),
    path("manage/academics/", include("academics.urls")),
    path("manage/students/", include("students.urls")),
    path("manage/results/", include("results.urls")),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("django-admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
