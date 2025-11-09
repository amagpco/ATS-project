from django.contrib import admin

from .models import ResumeAnalysis


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    """
    Simple admin that exposes AI results for auditing and manual QA. Keeping the
    match score sortable helps HR spot top candidates quickly.
    """

    list_display = ("application", "match_score", "cohere_model", "analyzed_at")
    list_filter = ("cohere_model", "analyzed_at")
    search_fields = (
        "application__full_name",
        "application__email",
        "application__job__title",
    )
    autocomplete_fields = ("application",)
    ordering = ("-analyzed_at",)
