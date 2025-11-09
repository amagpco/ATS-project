from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import UserAISettings

INPUT_CLASSES = (
    "block w-full rounded-xl border border-slate-300 bg-white/70 px-4 py-3 text-sm "
    "text-slate-700 shadow-sm placeholder:text-slate-400 focus:border-brand-500 "
    "focus:outline-none focus:ring-2 focus:ring-brand-400/50 dark:border-slate-700 "
    "dark:bg-slate-900/70 dark:text-slate-100 dark:placeholder:text-slate-500"
)

TOGGLE_CLASSES = "h-4 w-4 rounded border-slate-300 text-brand-500 focus:ring-brand-500 dark:border-slate-600 dark:bg-slate-900"


class LoginForm(AuthenticationForm):
    """
    Custom authentication form with Tailwind-friendly styling.
    """

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "class": INPUT_CLASSES,
                "placeholder": "Email or username",
            }
        ),
        label="Email or username",
    )

    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASSES,
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )

    remember_me = forms.BooleanField(
        required=False,
        label="Remember me",
        widget=forms.CheckboxInput(attrs={"class": TOGGLE_CLASSES}),
    )


class UserAISettingsForm(forms.ModelForm):
    job_temperature = forms.DecimalField(
        min_value=0,
        max_value=1,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASSES,
                "step": "0.01",
            }
        ),
    )
    resume_temperature = forms.DecimalField(
        min_value=0,
        max_value=1,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": INPUT_CLASSES,
                "step": "0.01",
            }
        ),
    )

    class Meta:
        model = UserAISettings
        fields = [
            "job_analysis_model",
            "job_temperature",
            "job_additional_prompt",
            "resume_analysis_model",
            "resume_temperature",
            "resume_additional_prompt",
            "auto_analyze_resumes",
            "enable_pdf_extraction",
            "enable_docx_extraction",
            "enable_text_extraction",
        ]
        widgets = {
            "job_analysis_model": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "e.g. command-a-03-2025",
                }
            ),
            "job_additional_prompt": forms.Textarea(
                attrs={
                    "class": INPUT_CLASSES + " min-h-[120px]",
                    "placeholder": "Optional additional instructions for job analysis prompts",
                }
            ),
            "resume_analysis_model": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "e.g. command-a-03-2025",
                }
            ),
            "resume_additional_prompt": forms.Textarea(
                attrs={
                    "class": INPUT_CLASSES + " min-h-[120px]",
                    "placeholder": "Optional additional instructions for resume analysis prompts",
                }
            ),
            "auto_analyze_resumes": forms.CheckboxInput(attrs={"class": TOGGLE_CLASSES}),
            "enable_pdf_extraction": forms.CheckboxInput(attrs={"class": TOGGLE_CLASSES}),
            "enable_docx_extraction": forms.CheckboxInput(attrs={"class": TOGGLE_CLASSES}),
            "enable_text_extraction": forms.CheckboxInput(attrs={"class": TOGGLE_CLASSES}),
        }

    def clean_job_analysis_model(self):
        return self.cleaned_data["job_analysis_model"].strip()

    def clean_resume_analysis_model(self):
        return self.cleaned_data["resume_analysis_model"].strip()

