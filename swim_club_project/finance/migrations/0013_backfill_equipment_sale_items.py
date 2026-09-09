from django.db import migrations
import re


def backfill_equipment_sale_items(apps, schema_editor):
    PaymentRecord = apps.get_model('finance', 'PaymentRecord')
    Equipment = apps.get_model('finance', 'Equipment')
    EquipmentSaleItem = apps.get_model('finance', 'EquipmentSaleItem')

    equipment = list(Equipment.objects.all())
    for payment in PaymentRecord.objects.filter(payment_type='equipment_sale'):
        if EquipmentSaleItem.objects.filter(payment_id=payment.pk).exists():
            continue

        lines = (payment.notes or '').splitlines()
        if not lines:
            continue
        first_line = lines[0]
        if not first_line.startswith('Malzemeler: '):
            continue

        sale_items = first_line.removeprefix('Malzemeler: ')
        child_items = []
        for item in equipment:
            match = re.search(
                rf'(?:^|,\s*){re.escape(item.name)}\s+x(\d+)(?:,|$)',
                sale_items,
            )
            if match:
                child_items.append(EquipmentSaleItem(
                    payment_id=payment.pk,
                    equipment_id=item.pk,
                    quantity=int(match.group(1)),
                    unit_price=item.price,
                ))
        EquipmentSaleItem.objects.bulk_create(child_items)


def reverse_backfill(apps, schema_editor):
    EquipmentSaleItem = apps.get_model('finance', 'EquipmentSaleItem')
    EquipmentSaleItem.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('finance', '0012_equipmentsaleitem'),
    ]

    operations = [
        migrations.RunPython(backfill_equipment_sale_items, reverse_backfill),
    ]
