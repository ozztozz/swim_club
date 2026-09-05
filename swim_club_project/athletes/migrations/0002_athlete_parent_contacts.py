from django.db import migrations, models


def copy_parent_details(apps, schema_editor):
    Athlete = apps.get_model('athletes', 'Athlete')
    for athlete in Athlete.objects.select_related('parent').all():
        parent = athlete.parent
        full_name = f'{parent.first_name} {parent.last_name}'.strip()
        athlete.parent_name = full_name or parent.email
        athlete.parent_email = parent.email
        athlete.parent_phone = parent.phone_number or ''
        athlete.save(update_fields=('parent_name', 'parent_email', 'parent_phone'))


class Migration(migrations.Migration):
    dependencies = [
        ('athletes', '0005_remove_athlete_regular_payment_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='athlete', name='parent_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='Veli'),
        ),
        migrations.AddField(
            model_name='athlete', name='parent_phone',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Veli Telefonu'),
        ),
        migrations.AddField(
            model_name='athlete', name='parent_email',
            field=models.EmailField(blank=True, default='', max_length=254, verbose_name='Veli E-postası'),
        ),
        migrations.AddField(
            model_name='athlete', name='phone_number',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Sporcu Telefonu'),
        ),
        migrations.RunPython(copy_parent_details, migrations.RunPython.noop),
        migrations.RemoveField(model_name='athlete', name='parent'),
        migrations.RenameField(model_name='athlete', old_name='parent_name', new_name='parent'),
        migrations.AlterField(
            model_name='athlete', name='parent',
            field=models.CharField(max_length=150, verbose_name='Veli'),
        ),
    ]