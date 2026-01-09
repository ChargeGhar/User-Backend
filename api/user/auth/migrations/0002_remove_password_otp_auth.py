# Generated migration for OTP-based authentication
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        # Remove password field and related fields from AbstractUser
        migrations.RemoveField(
            model_name='user',
            name='password',
        ),
        migrations.RemoveField(
            model_name='user',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='user',
            name='last_name',
        ),
        
        # Make email and phone_number nullable but ensure one exists
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(blank=True, max_length=150, null=True, unique=True),
        ),
        
        # Add constraint to ensure either email or phone exists
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(
                check=models.Q(('email__isnull', False)) | models.Q(('phone_number__isnull', False)),
                name='user_must_have_email_or_phone'
            ),
        ),
    ]