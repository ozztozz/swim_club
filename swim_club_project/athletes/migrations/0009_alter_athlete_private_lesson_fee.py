from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('athletes', '0008_rename_discount_percentage_athlete_private_lesson_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='athlete',
            name='private_lesson_fee',
            field=models.IntegerField(
                blank=True,
                help_text='Boş bırakılırsa özel ders ücreti uygulanmaz.',
                null=True,
                verbose_name='Özel ders ücreti',
            ),
        ),
    ]
