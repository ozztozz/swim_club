from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('athletes', '0009_alter_athlete_private_lesson_fee'),
        ('finance', '0016_equipment_is_active'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentStockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('stock_in', 'Stok girişi'), ('coach_transfer', 'Antrenöre teslim'), ('athlete_distribution', 'Sporcuya dağıtım'), ('coach_return', 'Antrenörden iade')], max_length=30)),
                ('quantity', models.PositiveIntegerField(verbose_name='Adet')),
                ('notes', models.TextField(blank=True, default='', verbose_name='Not')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('athlete', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipment_distributions', to='athletes.athlete', verbose_name='Sporcu')),
                ('coach', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipment_stock_movements', to=settings.AUTH_USER_MODEL, verbose_name='Antrenör')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_stock_movements', to=settings.AUTH_USER_MODEL)),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stock_movements', to='finance.equipment', verbose_name='Malzeme')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_movement', to='finance.paymentrecord', verbose_name='Tahsilat kaydı')),
            ],
            options={
                'verbose_name': 'Malzeme stok hareketi',
                'verbose_name_plural': 'Malzeme stok hareketleri',
                'ordering': ['-created_at', '-pk'],
            },
        ),
    ]
