# Generated manually - Remove PaymentWebhook model (nepal-gateways uses callbacks, not webhooks)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0006_paymentmethod_alter_refund_reason'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PaymentWebhook',
        ),
    ]