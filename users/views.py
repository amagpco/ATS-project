from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from .forms import LoginForm, UserAISettingsForm


class UserLoginView(LoginView):
    """
    Tailored login view that uses our styled form and supports both dashboard-first
    redirects and `next` query parameters while avoiding open redirect issues.
    """

    template_name = "users/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        remember = form.cleaned_data.get("remember_me")
        if not remember:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(None)
        return response

    def get_success_url(self):
        redirect_to = self.request.POST.get("next") or self.request.GET.get("next")
        if redirect_to and url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return redirect_to
        return settings.LOGIN_REDIRECT_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", "Sign in to Resume Analyzer ATS")
        return context


class AISettingsUpdateView(LoginRequiredMixin, View):
    """
    Allows users to manage their Cohere job/resume settings.
    """

    template_name = "dashboard/ai_settings.html"
    form_class = UserAISettingsForm

    def get(self, request: HttpRequest) -> HttpResponse:
        ai_settings = request.user.get_ai_settings()
        form = self.form_class(instance=ai_settings)
        context = {
            "form": form,
            "job_model_display": ai_settings.job_analysis_model,
            "resume_model_display": ai_settings.resume_analysis_model,
        }
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        ai_settings = request.user.get_ai_settings()
        form = self.form_class(request.POST, instance=ai_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "AI settings updated successfully.")
            return redirect("dashboard:ai_settings")
        context = {
            "form": form,
            "job_model_display": ai_settings.job_analysis_model,
            "resume_model_display": ai_settings.resume_analysis_model,
        }
        return render(request, self.template_name, context)
