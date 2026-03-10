from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("promotions", "0003_alter_couponusage_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="coupon",
            name="is_public",
            field=models.BooleanField(default=True),
        ),
    ]