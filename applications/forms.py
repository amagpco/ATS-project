from django import forms

from .models import Application, ApplicationStatus

INPUT_CLASS = (
    "block w-full rounded-xl border border-slate-300 bg-white/80 px-4 py-3 text-sm "
    "text-slate-700 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 "
    "focus:ring-brand-300 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-100"
)

UPLOAD_CLASS = (
    "block w-full rounded-xl border border-dashed border-slate-300 bg-white/60 px-4 py-6 "
    "text-sm text-slate-600 shadow-sm focus:border-brand-500 focus:outline-none "
    "focus:ring-2 focus:ring-brand-300 dark:border-slate-700 dark:bg-slate-900/50 "
    "dark:text-slate-200"
)


class ApplicationUploadForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["full_name", "email", "resume_file"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Candidate full name",
                    "autofocus": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "candidate@email.com",
                }
            ),
            "resume_file": forms.FileInput(
                attrs={
                    "class": UPLOAD_CLASS,
                    "accept": ".pdf,.doc,.docx,.txt",
                }
            ),
        }

    def clean_resume_file(self):
        resume = self.cleaned_data.get("resume_file")
        if not resume:
            raise forms.ValidationError("Please upload the candidate's resume.")
        if resume.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Resume file must be smaller than 10MB.")
        return resume


class ApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["full_name", "email", "resume_file"]
        widgets = ApplicationUploadForm.Meta.widgets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resume_file"].required = False
        self.fields["resume_file"].widget.attrs["class"] = UPLOAD_CLASS


class ApplicationStatusForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=ApplicationStatus.choices,
        widget=forms.Select(
            attrs={
                "class": INPUT_CLASS.replace("px-4 py-3", "px-4 py-2"),
            }
        ),
    )

    class Meta:
        model = Application
        fields = ["status"]

