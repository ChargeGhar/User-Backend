# Generated manually on 2026-02-22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        # Update ContentPage choices - remove 'faq', add 'renting-policy'
        migrations.AlterField(
            model_name='contentpage',
            name='page_type',
            field=models.CharField(
                choices=[
                    ('terms-of-service', 'Terms of Service'),
                    ('privacy-policy', 'Privacy Policy'),
                    ('about', 'About Us'),
                    ('contact', 'Contact Us'),
                    ('renting-policy', 'Renting Policy')
                ],
                max_length=255,
                unique=True
            ),
        ),

        # Delete ContactInfo model if it exists
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS contact_info CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
