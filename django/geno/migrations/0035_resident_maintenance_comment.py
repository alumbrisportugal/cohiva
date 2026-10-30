from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("geno", "0034_resident_maintenance_request"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ResidentMaintenanceComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField(max_length=2000)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alumbris_maintenance_comments", to=settings.AUTH_USER_MODEL)),
                ("ticket", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="geno.residentmaintenancerequest")),
            ],
            options={"ordering": ("created_at", "pk")},
        ),
    ]
