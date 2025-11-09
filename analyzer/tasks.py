import logging
from decimal import Decimal

from celery import shared_task
from django.db import transaction

from analyzer.models import ResumeAnalysis
from analyzer.services import (
    DEFAULT_CHAT_MODEL,
    CohereServiceError,
    analyze_resume_with_cohere,
)
from applications.models import Application, ApplicationStatus

logger = logging.getLogger(__name__)


def process_application_analysis(application: Application, settings_obj=None) -> None:
    """
    Core business logic shared by the Celery task and synchronous fallbacks.
    """

    if settings_obj is None:
        settings_obj = application.job.created_by.get_ai_settings()

    if not settings_obj.auto_analyze_resumes:
        application.status = ApplicationStatus.NEEDS_REVIEW
        application.save(update_fields=["status"])
        return

    if not application.resume_text:
        application.status = ApplicationStatus.NEEDS_REVIEW
        application.save(update_fields=["status"])
        return

    job = application.job
    result = analyze_resume_with_cohere(
        resume_text=application.resume_text,
        job_description=job.description,
        job_title=job.title,
        model=settings_obj.resume_analysis_model,
        temperature=float(settings_obj.resume_temperature),
        extra_instructions=settings_obj.resume_additional_prompt,
    )

    match_score = Decimal(min(max(result.get("match_score", 0.0), 0.0), 1.0)).quantize(Decimal("0.0001"))

    with transaction.atomic():
        ResumeAnalysis.objects.update_or_create(
            application=application,
            defaults={
                "match_score": match_score,
                "summary": result.get("summary", ""),
                "improvements": {
                    "suggestions": result.get("improvements", []),
                    "recommended_skills": result.get("recommended_skills", []),
                },
                "cohere_model": result.get("model_used", DEFAULT_CHAT_MODEL),
            },
        )
        application.status = ApplicationStatus.ANALYZED
        application.save(update_fields=["status"])


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def analyze_application_task(self, application_id: str) -> None:
    try:
        application = Application.objects.select_related("job").get(pk=application_id)
    except Application.DoesNotExist:  # pragma: no cover - defensive
        logger.warning("Application %s no longer exists; skipping analysis.", application_id)
        return

    if application.status != ApplicationStatus.PROCESSING:
        application.status = ApplicationStatus.PROCESSING
        application.save(update_fields=["status"])

    try:
        process_application_analysis(application)
    except CohereServiceError as exc:
        logger.error("Cohere analysis failed for application %s: %s", application_id, exc)
        application.status = ApplicationStatus.NEEDS_REVIEW
        application.save(update_fields=["status"])
        raise self.retry(exc=exc, countdown=180)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error analysing application %s", application_id)
        application.status = ApplicationStatus.NEEDS_REVIEW
        application.save(update_fields=["status"])
        raise

