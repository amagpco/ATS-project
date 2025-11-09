from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel, UUIDModel


def resume_upload_path(instance: "Application", filename: str) -> str:
    """
    Build a deterministic upload path for resume files.

    Files are organized by job ID to keep storage tidy and fast to look up
    during reviews.
    """

    return f"resumes/{instance.job_id}/{filename}"


class ApplicationStatus(models.TextChoices):
    SUBMITTED = "submitted", _("Submitted")
    PROCESSING = "processing", _("Processing")
    ANALYZED = "analyzed", _("Analyzed")
    FIRST_INTERVIEW = "first_interview", _("First Interview")
    SECOND_INTERVIEW = "second_interview", _("Second Interview")
    ACCEPTED = "accepted", _("Accepted")
    REJECTED = "rejected", _("Rejected")
    NEEDS_REVIEW = "needs_review", _("Needs Review")


class Application(UUIDModel, TimeStampedModel):
    """
    Represents an application submitted for a specific job posting.

    Resume files are uploaded and text is extracted for analysis. The status
    field tracks where the application sits in the review pipeline.
    """

    job = models.ForeignKey(
        "jobs.JobPosition",
        related_name="applications",
        on_delete=models.CASCADE,
        help_text=_("Job position the candidate applied for."),
    )
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    resume_file = models.FileField(upload_to=resume_upload_path)
    resume_text = models.TextField(
        blank=True,
        help_text=_("Plain text extracted from the uploaded resume."),
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="uploaded_applications",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("User who uploaded the resume."),
    )
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
        db_index=True,
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("application")
        verbose_name_plural = _("applications")
        indexes = [
            models.Index(fields=("status",)),
            models.Index(fields=("created_at",)),
            models.Index(fields=("uploaded_by",)),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("job", "email"),
                name="unique_application_email_per_job",
            )
        ]

    def __str__(self) -> str:
        return f"{self.full_name} - {self.job.title}"

    @property
    def has_analysis(self) -> bool:
        return hasattr(self, "analysis")
