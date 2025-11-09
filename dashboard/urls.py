from django.urls import path

from . import views


app_name = "dashboard"


urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("jobs/", views.job_list_view, name="job_list"),
    path("jobs/create/", views.job_create_view, name="job_create"),
    path("jobs/import/", views.job_import_view, name="job_import"),
    path("jobs/<uuid:job_id>/", views.job_detail_view, name="job_detail"),
    path("jobs/<uuid:job_id>/edit/", views.job_update_view, name="job_edit"),
    path("jobs/<uuid:job_id>/delete/", views.job_delete_view, name="job_delete"),
    path(
        "jobs/<uuid:job_id>/applications/upload/",
        views.application_upload_view,
        name="application_upload",
    ),
    path("applications/", views.application_list_view, name="application_list"),
    path(
        "applications/<uuid:application_id>/edit/",
        views.application_edit_view,
        name="application_edit",
    ),
    path(
        "applications/<uuid:application_id>/status/",
        views.application_status_update_view,
        name="application_status",
    ),
    path(
        "applications/<uuid:application_id>/",
        views.application_detail_view,
        name="application_detail",
    ),
    path(
        "applications/<uuid:application_id>/download/",
        views.application_resume_download,
        name="application_download",
    ),
    path("settings/ai/", views.user_ai_settings_view, name="ai_settings"),
]

