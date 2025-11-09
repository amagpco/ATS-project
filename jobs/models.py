from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel, UUIDModel


class JobPosition(UUIDModel, TimeStampedModel):
    """
    Represents an open role that HR or Admin users can create and manage.

    Applications are attached to a specific job position, and AI analysis uses
    the job description to determine candidate fit.
    """

    title = models.CharField(max_length=255, help_text=_("Public title of the job."))
    description = models.TextField(help_text=_("Detailed description used for AI matching."))
    department = models.CharField(
        max_length=120,
        blank=True,
        help_text=_("Optional department or team for reporting."),
    )
    source_url = models.URLField(
        blank=True,
        help_text=_("Original source URL if this job was imported from an external site."),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="job_positions",
        on_delete=models.CASCADE,
        help_text=_("User who created the job posting."),
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("job position")
        verbose_name_plural = _("job positions")
        indexes = [
            models.Index(fields=("department",)),
            models.Index(fields=("created_at",)),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.department or _('General')})"
