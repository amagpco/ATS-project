from django import forms

from .models import JobPosition


INPUT_CLASSES = (
    "block w-full rounded-xl border border-slate-300 bg-white/80 px-4 py-3 text-sm "
    "text-slate-700 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 "
    "focus:ring-brand-300 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-100"
)

TEXTAREA_CLASSES = INPUT_CLASSES + " min-h-[200px]"


class JobImportForm(forms.Form):
    job_url = forms.URLField(
        label="Job profile URL",
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://careers.example.com/job/software-engineer",
                "class": INPUT_CLASSES,
            }
        ),
        help_text="Paste a public job posting URL. Supported pages should contain readable text.",
    )


class JobPositionCreateForm(forms.ModelForm):
    class Meta:
        model = JobPosition
        fields = ["title", "department", "description", "source_url"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "e.g. Senior Backend Engineer",
                    "autofocus": True,
                }
            ),
            "department": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "e.g. Engineering",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASSES,
                    "placeholder": "Describe the role, responsibilities, and requirements...",
                }
            ),
            "source_url": forms.URLInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Optional: original posting URL",
                }
            ),
        }


class JobPositionUpdateForm(JobPositionCreateForm):
    class Meta(JobPositionCreateForm.Meta):
        pass

