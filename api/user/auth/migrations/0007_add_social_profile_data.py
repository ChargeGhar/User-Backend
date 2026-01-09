# Generated manually to add social profile data field to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_add_social_auth_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='social_profile_data',
            field=models.JSONField(default=dict, blank=True),
        ),
    ]