from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    ADMIN = "admin", _("Administrator")
    HR = "hr", _("HR Manager")


class User(AbstractUser):
    """
    Custom user model that adds role-based access control.

    We extend Django's AbstractUser to keep the built-in authentication stack
    (password hashing, permissions, groups) and simply add HR-specific fields.
    """

    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.HR,
        help_text=_("Determines access to HR and administrative features."),
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ("username",)

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_hr(self) -> bool:
        return self.role == UserRole.HR

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def get_ai_settings(self) -> "UserAISettings":
        """
        Returns the user's AI settings, creating defaults if necessary.
        """

        try:
            return self.ai_settings
        except UserAISettings.DoesNotExist:
            return UserAISettings.objects.create(user=self)


class UserAISettings(models.Model):
    """
    Stores per-user configuration for AI-powered features (job imports, resume analysis).
    """

    user = models.OneToOneField(
        User,
        related_name="ai_settings",
        on_delete=models.CASCADE,
    )
    job_analysis_model = models.CharField(
        max_length=120,
        default="command-a-03-2025",
        help_text=_("Cohere model used when analysing job postings."),
    )
    job_temperature = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.15"),
        help_text=_("Sampling temperature for job analysis requests."),
    )
    job_additional_prompt = models.TextField(
        blank=True,
        help_text=_("Optional extra instructions appended to job analysis prompts."),
    )
    resume_analysis_model = models.CharField(
        max_length=120,
        default="command-a-03-2025",
        help_text=_("Cohere model used when analysing resumes."),
    )
    resume_temperature = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.15"),
        help_text=_("Sampling temperature for resume analysis requests."),
    )
    resume_additional_prompt = models.TextField(
        blank=True,
        help_text=_("Optional extra instructions appended to resume analysis prompts."),
    )
    auto_analyze_resumes = models.BooleanField(
        default=True,
        help_text=_("Automatically trigger AI analysis after uploading a resume."),
    )
    enable_pdf_extraction = models.BooleanField(
        default=True,
        help_text=_("Allow automatic text extraction from PDF resumes."),
    )
    enable_docx_extraction = models.BooleanField(
        default=True,
        help_text=_("Allow automatic text extraction from DOCX resumes."),
    )
    enable_text_extraction = models.BooleanField(
        default=True,
        help_text=_("Allow automatic text extraction from plain text resumes."),
    )

    class Meta:
        verbose_name = _("AI setting")
        verbose_name_plural = _("AI settings")

    def __str__(self) -> str:
        return f"AI settings for {self.user}"


@receiver(post_save, sender=User)
def ensure_user_ai_settings(sender, instance: User, created: bool, **kwargs) -> None:
    if created:
        UserAISettings.objects.create(user=instance)
