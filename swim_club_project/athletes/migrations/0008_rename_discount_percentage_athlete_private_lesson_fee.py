from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('athletes', '0007_alter_athlete_custom_fee_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='athlete',
            old_name='discount_percentage',
            new_name='private_lesson_fee',
        ),
    ]