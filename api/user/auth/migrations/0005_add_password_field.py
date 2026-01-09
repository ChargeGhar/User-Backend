# Generated manually to add password field back to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_user_options_alter_user_managers_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='password',
            field=models.CharField(max_length=128, verbose_name='password', default=''),
            preserve_default=False,
        ),
    ]