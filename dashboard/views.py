from __future__ import annotations

from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from django.utils import timezone

from analyzer.models import ResumeAnalysis
from analyzer.services import CohereServiceError
from analyzer.tasks import analyze_application_task, process_application_analysis
from applications.forms import (
    ApplicationStatusForm,
    ApplicationUpdateForm,
    ApplicationUploadForm,
)
from applications.models import Application, ApplicationStatus
from applications.utils import extract_resume_text
from jobs.forms import JobImportForm, JobPositionCreateForm, JobPositionUpdateForm
from jobs.models import JobPosition
from jobs.services import JobImportError, import_job_from_url
from users.forms import UserAISettingsForm


@dataclass
class DashboardMetrics:
    total_jobs: int
    total_applications: int
    pending_applications: int
    analyzed_applications: int
    top_candidates: list[ResumeAnalysis]


def _get_dashboard_metrics() -> DashboardMetrics:
    total_jobs = JobPosition.objects.count()
    total_applications = Application.objects.count()
    pending_applications = Application.objects.filter(
        status__in=[ApplicationStatus.SUBMITTED, ApplicationStatus.PROCESSING]
    ).count()
    analyzed_applications = Application.objects.filter(
        status=ApplicationStatus.ANALYZED
    ).count()
    top_candidates = (
        ResumeAnalysis.objects.select_related("application", "application__job")
        .order_by("-match_score")[:5]
    )
    return DashboardMetrics(
        total_jobs=total_jobs,
        total_applications=total_applications,
        pending_applications=pending_applications,
        analyzed_applications=analyzed_applications,
        top_candidates=list(top_candidates),
    )


@login_required
def dashboard_home(request: HttpRequest) -> HttpResponse:
    metrics = _get_dashboard_metrics()
    recent_jobs = JobPosition.objects.select_related("created_by").order_by("-created_at")[:5]
    recent_applications = (
        Application.objects.select_related("job")
        .order_by("-created_at")[:5]
    )
    context = {
        "metrics": metrics,
        "recent_jobs": recent_jobs,
        "recent_applications": recent_applications,
        "current_time": timezone.now(),
    }
    return render(request, "dashboard/index.html", context)


@login_required
def job_list_view(request: HttpRequest) -> HttpResponse:
    jobs = JobPosition.objects.select_related("created_by").order_by("-created_at")
    return render(request, "dashboard/job_list.html", {"jobs": jobs})


@login_required
def job_import_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = JobImportForm(request.POST)
        if form.is_valid():
            job_url = form.cleaned_data["job_url"]
            try:
                user_settings = request.user.get_ai_settings()
                result = import_job_from_url(
                    job_url,
                    created_by=request.user,
                    user_settings=user_settings,
                )
            except JobImportError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    f"Imported job “{result.job.title}” from the provided URL.",
                )
                return redirect("dashboard:job_list")
    else:
        form = JobImportForm()

    return render(request, "dashboard/job_import.html", {"form": form})


@login_required
def job_create_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = JobPositionCreateForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.created_by = request.user
            job.save()
            messages.success(request, f'Job "{job.title}" created successfully.')
            return redirect("dashboard:job_list")
    else:
        form = JobPositionCreateForm()

    return render(
        request,
        "dashboard/job_form.html",
        {"form": form, "is_edit": False, "page_title": "Create Job Position"},
    )


@login_required
def job_update_view(request: HttpRequest, job_id: str) -> HttpResponse:
    job = get_object_or_404(
        JobPosition.objects.select_related("created_by"),
        pk=job_id,
    )

    if request.method == "POST":
        form = JobPositionUpdateForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, f'Job "{job.title}" updated successfully.')
            return redirect("dashboard:job_detail", job_id=job.pk)
    else:
        form = JobPositionUpdateForm(instance=job)

    return render(
        request,
        "dashboard/job_form.html",
        {
            "form": form,
            "is_edit": True,
            "page_title": f"Edit {job.title}",
            "job": job,
        },
    )


@login_required
def job_delete_view(request: HttpRequest, job_id: str) -> HttpResponse:
    job = get_object_or_404(
        JobPosition.objects.select_related("created_by"),
        pk=job_id,
    )

    if request.method == "POST":
        job_title = job.title
        job.delete()
        messages.success(request, f'Job "{job_title}" has been deleted.')
        return redirect("dashboard:job_list")

    return render(
        request,
        "dashboard/job_confirm_delete.html",
        {"job": job},
    )


@login_required
def application_upload_view(request: HttpRequest, job_id: str) -> HttpResponse:
    job = get_object_or_404(
        JobPosition.objects.select_related("created_by"),
        pk=job_id,
    )

    uploader_settings = request.user.get_ai_settings()
    job_owner_settings = job.created_by.get_ai_settings()

    if request.method == "POST":
        form = ApplicationUploadForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.status = ApplicationStatus.SUBMITTED
            application.save()

            resume_text = extract_resume_text(
                application.resume_file.name,
                settings=uploader_settings,
            )
            if resume_text:
                application.resume_text = resume_text
            else:
                messages.warning(
                    request,
                    "Uploaded resume could not be parsed automatically. Marked for manual review.",
                )
                application.status = ApplicationStatus.NEEDS_REVIEW
                application.save(update_fields=["resume_text", "status"])
                return redirect("dashboard:application_detail", application_id=application.pk)

            if not job_owner_settings.auto_analyze_resumes:
                application.status = ApplicationStatus.NEEDS_REVIEW
                application.save(update_fields=["resume_text", "status"])
                messages.info(
                    request,
                    "Resume uploaded. Automatic AI analysis is disabled; please review manually.",
                )
                return redirect("dashboard:application_detail", application_id=application.pk)

            application.status = ApplicationStatus.PROCESSING
            application.save(update_fields=["resume_text", "status"])

            try:
                analyze_application_task.delay(str(application.pk))
            except Exception:  # pragma: no cover - defensive
                try:
                    process_application_analysis(application, settings_obj=job_owner_settings)
                except CohereServiceError:
                    application.status = ApplicationStatus.NEEDS_REVIEW
                    application.save(update_fields=["status"])
                    messages.error(
                        request,
                        "Resume saved but AI analysis failed. Review the application manually.",
                    )
                else:
                    application.refresh_from_db(fields=["status"])
                    messages.success(
                        request,
                        f"Resume uploaded for {application.full_name}. AI analysis completed.",
                    )
            else:
                messages.success(
                    request,
                    f"Resume uploaded for {application.full_name}. AI analysis is running.",
                )

            return redirect("dashboard:application_detail", application_id=application.pk)
    else:
        form = ApplicationUploadForm()

    return render(
        request,
        "dashboard/application_upload.html",
        {"form": form, "job": job},
    )


@login_required
def application_edit_view(request: HttpRequest, application_id: str) -> HttpResponse:
    application = get_object_or_404(
        Application.objects.select_related("job"),
        pk=application_id,
    )
    form = ApplicationUpdateForm(request.POST or None, request.FILES or None, instance=application)

    if request.method == "POST" and form.is_valid():
        application = form.save()
        resume_updated = "resume_file" in form.changed_data and application.resume_file

        if resume_updated:
            resume_text = extract_resume_text(application.resume_file.name)
            if resume_text:
                application.resume_text = resume_text
                application.status = ApplicationStatus.PROCESSING
                application.save(update_fields=["resume_file", "resume_text", "status", "full_name", "email"])
                try:
                    analyze_application_task.delay(str(application.pk))
                except Exception:
                    try:
                        process_application_analysis(application)
                    except CohereServiceError:
                        application.status = ApplicationStatus.NEEDS_REVIEW
                        application.save(update_fields=["status"])
                        messages.error(
                            request,
                            "Resume updated but AI analysis failed. Please review manually.",
                        )
                    else:
                        application.refresh_from_db(fields=["status"])
                        messages.success(
                            request,
                            "Resume updated and re-analysed successfully.",
                        )
                        return redirect("dashboard:application_detail", application_id=application.pk)
                else:
                    messages.success(
                        request,
                        "Resume updated. AI re-analysis is running in the background.",
                    )
            else:
                application.resume_text = ""
                application.status = ApplicationStatus.NEEDS_REVIEW
                application.save(update_fields=["resume_file", "resume_text", "status", "full_name", "email"])
                messages.warning(
                    request,
                    "Updated resume could not be parsed automatically. Marked for manual review.",
                )
                return redirect("dashboard:application_detail", application_id=application.pk)
        else:
            application.save(update_fields=["full_name", "email"])
            messages.success(request, "Application details updated.")

        return redirect("dashboard:application_detail", application_id=application.pk)

    return render(
        request,
        "dashboard/application_edit.html",
        {"form": form, "application": application},
    )


@login_required
def application_status_update_view(request: HttpRequest, application_id: str) -> HttpResponse:
    application = get_object_or_404(Application.objects.select_related("job"), pk=application_id)

    if request.method != "POST":  # safeguard
        return redirect("dashboard:application_detail", application_id=application.pk)

    form = ApplicationStatusForm(request.POST, instance=application)
    if form.is_valid():
        previous_label = application.get_status_display()
        updated_application = form.save()
        messages.success(
            request,
            f"Status updated from {previous_label} to {updated_application.get_status_display()}.",
        )
    else:
        messages.error(request, "Unable to update application status. Please try again.")

    return redirect("dashboard:application_detail", application_id=application.pk)


@login_required
def application_list_view(request: HttpRequest) -> HttpResponse:
    status_param = request.GET.get("status")
    job_param = request.GET.get("job")
    search_param = request.GET.get("q")

    applications = Application.objects.select_related("job", "analysis").order_by("-created_at")

    if status_param:
        applications = applications.filter(status=status_param)

    if job_param:
        applications = applications.filter(job__title__icontains=job_param)

    if search_param:
        applications = applications.filter(
            Q(full_name__icontains=search_param)
            | Q(email__icontains=search_param)
            | Q(job__title__icontains=search_param)
        )

    context = {
        "applications": applications,
        "status_filter": status_param or "",
        "job_filter": job_param or "",
        "search_query": search_param or "",
        "status_choices": ApplicationStatus.choices,
    }
    return render(request, "dashboard/application_list.html", context)


@login_required
def job_detail_view(request: HttpRequest, job_id: str) -> HttpResponse:
    job = get_object_or_404(
        JobPosition.objects.select_related("created_by"),
        pk=job_id,
    )
    applications_qs = (
        Application.objects.filter(job=job)
        .select_related("analysis")
        .order_by("-created_at")
    )
    total_applications = applications_qs.count()
    analyzed_applications = applications_qs.filter(analysis__isnull=False).count()
    return render(
        request,
        "dashboard/job_detail.html",
        {
            "job": job,
            "applications": applications_qs,
            "total_applications": total_applications,
            "analyzed_applications": analyzed_applications,
        },
    )


@login_required
def application_detail_view(request: HttpRequest, application_id: str) -> HttpResponse:
    application = get_object_or_404(
        Application.objects.select_related("job", "analysis"),
        pk=application_id,
    )
    analysis = getattr(application, "analysis", None)
    status_form = ApplicationStatusForm(instance=application)
    return render(
        request,
        "dashboard/application_detail.html",
        {
            "application": application,
            "analysis": analysis,
            "status_form": status_form,
        },
    )


@login_required
def user_ai_settings_view(request: HttpRequest) -> HttpResponse:
    settings_obj = request.user.get_ai_settings()

    if request.method == "POST":
        form = UserAISettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "AI configuration updated successfully.")
            return redirect("dashboard:ai_settings")
    else:
        form = UserAISettingsForm(instance=settings_obj)

    context = {
        "form": form,
        "job_model_display": settings_obj.job_analysis_model,
        "resume_model_display": settings_obj.resume_analysis_model,
    }
    return render(request, "dashboard/ai_settings.html", context)


@login_required
def application_resume_download(request: HttpRequest, application_id: str) -> HttpResponse:
    application = get_object_or_404(Application, pk=application_id)
    if not application.resume_file:
        raise Http404("Resume file not found.")
    response = FileResponse(
        application.resume_file.open("rb"),
        as_attachment=True,
        filename=application.resume_file.name.split("/")[-1],
    )
    return response
