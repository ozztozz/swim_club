from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('athletes', '0005_remove_athlete_regular_payment_date_and_more'),
        ('athletes', '0002_athlete_parent_contacts'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='athlete',
            name='status',
        ),
    ]
