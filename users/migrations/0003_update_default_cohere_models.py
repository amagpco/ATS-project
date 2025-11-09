from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_useraisettings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="useraisettings",
            name="job_analysis_model",
            field=models.CharField(
                default="command-a-03-2025",
                help_text="Cohere model used when analysing job postings.",
                max_length=120,
            ),
        ),
        migrations.AlterField(
            model_name="useraisettings",
            name="resume_analysis_model",
            field=models.CharField(
                default="command-a-03-2025",
                help_text="Cohere model used when analysing resumes.",
                max_length=120,
            ),
        ),
    ]

