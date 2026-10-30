from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("geno", "0032_tenantsview_active_fix")]

    operations = [
        migrations.AddField(
            model_name="document",
            name="resident_visible",
            field=models.BooleanField(
                default=False,
                db_index=True,
                verbose_name="Visible to contract residents",
            ),
        ),
    ]
