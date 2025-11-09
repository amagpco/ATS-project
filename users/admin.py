from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserAISettings, UserRole


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Custom admin configuration that surfaces user roles and ensures email
    uniqueness is enforced through the admin interface. We keep most of the
    built-in Django behaviours (password management, permissions) while adding
    HR-specific fields to the interface.
    """

    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "role", "password1", "password2"),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["role"].initial = UserRole.HR
        return form


@admin.register(UserAISettings)
class UserAISettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "job_analysis_model", "resume_analysis_model", "auto_analyze_resumes")
    search_fields = ("user__username", "user__email", "job_analysis_model", "resume_analysis_model")
    readonly_fields = ("user",)
