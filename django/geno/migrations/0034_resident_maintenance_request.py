from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("geno", "0033_document_resident_visible"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ResidentMaintenanceRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                ("description", models.TextField(max_length=3000)),
                ("status", models.CharField(choices=[("open", "Aberto"), ("in_progress", "Em tratamento"), ("resolved", "Resolvido"), ("closed", "Fechado")], default="open", max_length=20)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("ts_modified", models.DateTimeField(auto_now=True)),
                ("rental_unit", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alumbris_maintenance_requests", to="geno.rentalunit")),
                ("resident", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="alumbris_maintenance_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at", "-pk")},
        ),
    ]
