from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0015_expense_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipment',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Aktif mi?'),
        ),
    ]
