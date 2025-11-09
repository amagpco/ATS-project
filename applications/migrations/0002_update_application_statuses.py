from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="application",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "Submitted"),
                    ("processing", "Processing"),
                    ("analyzed", "Analyzed"),
                    ("first_interview", "First Interview"),
                    ("second_interview", "Second Interview"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                    ("needs_review", "Needs Review"),
                ],
                db_index=True,
                default="submitted",
                max_length=20,
            ),
        ),
    ]

