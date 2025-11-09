from django.contrib import admin

from .models import Application, ApplicationStatus


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    Admin interface to review candidate applications, filter by job or status,
    and quickly identify whether AI analysis has been completed.
    """

    list_display = (
        "full_name",
        "email",
        "job",
        "status",
        "created_at",
        "analysis_completed",
    )
    list_filter = ("status", "created_at", "job")
    search_fields = ("full_name", "email", "job__title")
    autocomplete_fields = ("job",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "job",
                    "full_name",
                    "email",
                    "resume_file",
                    "resume_text",
                    "status",
                )
            },
        ),
        (
            "Timestamps",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description="Analyzed", boolean=True)
    def analysis_completed(self, obj: Application) -> bool:
        return obj.has_analysis
