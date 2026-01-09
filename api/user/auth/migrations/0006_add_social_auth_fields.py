# Generated migration for social authentication fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_add_password_field'),
    ]

    operations = [
        # Add social authentication fields
        migrations.AddField(
            model_name='user',
            name='google_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='user',
            name='apple_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='user',
            name='social_provider',
            field=models.CharField(
                choices=[
                    ('EMAIL', 'Email'), 
                    ('PHONE', 'Phone'), 
                    ('GOOGLE', 'Google'), 
                    ('APPLE', 'Apple')
                ],
                default='EMAIL',
                help_text='Primary authentication method used by the user',
                max_length=20
            ),
        ),
        
        # Remove old constraint
        migrations.RemoveConstraint(
            model_name='user',
            name='user_must_have_email_or_phone',
        ),
        
        # Add new constraint that includes social auth fields
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(
                check=models.Q(
                    ('email__isnull', False)
                ) | models.Q(
                    ('phone_number__isnull', False)
                ) | models.Q(
                    ('google_id__isnull', False)
                ) | models.Q(
                    ('apple_id__isnull', False)
                ),
                name='user_must_have_identifier'
            ),
        ),
    ]