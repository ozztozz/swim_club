from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0017_equipment_stock_movement'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipmentstockmovement',
            name='sale_item',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='stock_movements',
                to='finance.equipmentsaleitem',
                verbose_name='Satış satırı',
            ),
        ),
    ]
