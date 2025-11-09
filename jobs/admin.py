from django.contrib import admin

from .models import JobPosition


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    """
    Present job positions with quick filters for department and creator, making
    it easy for HR teams to manage a growing catalogue of open roles.
    """

    list_display = ("title", "department", "created_by", "created_at", "source_url")
    list_filter = ("department", "created_at")
    search_fields = ("title", "department", "description", "created_by__username", "source_url")
    autocomplete_fields = ("created_by",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
