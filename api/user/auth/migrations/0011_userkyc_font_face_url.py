from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_user_is_partner"),
    ]

    operations = [
        migrations.AddField(
            model_name="userkyc",
            name="font_face_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
