from django.db import migrations


def copy_latest_custom_fees(apps, schema_editor):
    Athlete = apps.get_model('athletes', 'Athlete')
    AthleteFeeHistory = apps.get_model('finance', 'AthleteFeeHistory')

    for athlete in Athlete.objects.filter(custom_fee__isnull=True):
        latest_fee = AthleteFeeHistory.objects.filter(athlete_id=athlete.id).order_by('-start_date').first()
        if latest_fee:
            Athlete.objects.filter(pk=athlete.pk).update(custom_fee=latest_fee.monthly_fee)


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0008_alter_paymentrecord_payment_type'),
    ]

    operations = [
        migrations.RunPython(copy_latest_custom_fees, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='AthleteFeeHistory',
        ),
    ]
