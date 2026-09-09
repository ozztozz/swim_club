from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from teams.models import Team
from athletes.models import Athlete
from finance.models import Equipment, EquipmentSaleItem, PaymentRecord, ExpenseCategory, Expense, TeamFeeHistory
from finance.services import get_athlete_fee_for_period, get_or_create_monthly_payments, get_financial_summary

User = get_user_model()

class FinanceModelAndServiceTests(TestCase):

    def setUp(self):
        # Admin kullanıcısı
        self.user = User.objects.create_user(
            username='adminuser',
            password='password123',
            email='admin@alphakulup.com',  # <-- Benzersiz email
            role='admin'
        )
        
        # Veli kullanıcısı (parent_id kısıtlaması için gerekli)
        self.parent_user = User.objects.create_user(
            username='parentuser',
            password='password123',
            
            email='parent@alphakulup.com', # <-- Benzersiz email
            first_name='Ahmet',
            last_name='Veli',
            role='parent'
        )
        
        # Takım
        self.team = Team.objects.create(
            name="A Takımı",
            is_active=True
        )
        TeamFeeHistory.objects.create(
            team=self.team,
            monthly_fee=Decimal('1500.00'),
            start_date=date(2026, 1, 1),
        )
        
        # Onaylı Sporcular (parent ve joined_date eklendi)
        self.athlete1 = Athlete.objects.create(
            first_name="Ahmet",
            last_name="Yılmaz",
            birth_date=date(2012, 5, 10),
            joined_date=date(2026, 1, 1),
            parent=self.parent_user,  # <-- Eklendi
            gender="M",
            is_active=True,
            team=self.team
        )
        self.athlete2 = Athlete.objects.create(
            first_name="Ayşe",
            last_name="Kaya",
            birth_date=date(2013, 8, 20),
            joined_date=date(2026, 1, 1),
            parent=self.parent_user,  # <-- Eklendi
            gender="F",
            is_active=True,
            team=self.team,
            custom_fee=Decimal('1000.00')
        )
        # Onay bekleyen sporcu
        self.athlete_pending = Athlete.objects.create(
            first_name="Mehmet",
            last_name="Demir",
            birth_date=date(2014, 1, 15),
            joined_date=date(2026, 1, 1),
            parent=self.parent_user,  # <-- Eklendi
            is_active=True,
            gender="M"
        )
        
        # Harcama Kategorisi
        self.category = ExpenseCategory.objects.create(
            name="Havuz Kirası",
            description="Aylık havuz kulvar kiraları"
        )

    def test_payment_record_is_overdue_property(self):
        # Past due date and pending status -> overdue True
        past_payment = PaymentRecord.objects.create(
            athlete=self.athlete1,
            period="2026-07",
            amount=Decimal('1500.00'),
            status="pending",
            due_date=date.today() - timedelta(days=5)
        )
        self.assertTrue(past_payment.is_overdue)

        # Paid status -> overdue False even if past due date
        past_payment.status = "paid"
        past_payment.save()
        self.assertFalse(past_payment.is_overdue)

        # Future due date -> overdue False
        future_payment = PaymentRecord.objects.create(
            athlete=self.athlete2,
            period="2026-09",
            amount=Decimal('1000.00'),
            status="pending",
            due_date=date.today() + timedelta(days=10)
        )
        self.assertFalse(future_payment.is_overdue)

    def test_athlete_equipment_sale_creates_paid_payment_record(self):
        equipment = Equipment.objects.create(
            name='Kulüp Tişörtü',
            price=Decimal('750.00'),
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('athlete-manage-equipment-sale-create', args=[self.athlete1.pk]),
            data={
                f'equipment_{equipment.pk}': '2',
                'payment_method': 'cash',
                'status': 'paid',
                'notes': 'Deneme satışı',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 204)
        payment = PaymentRecord.objects.get(payment_type='equipment_sale')
        self.assertEqual(payment.athlete, self.athlete1)
        self.assertEqual(payment.amount, Decimal('1500.00'))
        self.assertEqual(payment.status, 'paid')
        self.assertEqual(payment.collected_by, self.user)
        self.assertIn('Malzemeler: Kulüp Tişörtü x2', payment.notes)
        sale_item = EquipmentSaleItem.objects.get(payment=payment)
        self.assertEqual(sale_item.quantity, 2)
        self.assertEqual(sale_item.unit_price, Decimal('750.00'))

        equipment.price = Decimal('900.00')
        equipment.save(update_fields=('price',))
        sale_item.refresh_from_db()
        self.assertEqual(sale_item.unit_price, Decimal('750.00'))

        edit_response = self.client.post(
            reverse('athlete-manage-equipment-sale-edit', args=[self.athlete1.pk, payment.pk]),
            data={
                f'equipment_{equipment.pk}': '3',
                'payment_method': 'cash',
                'status': 'paid',
                'notes': 'Güncellenmiş satış',
            },
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(edit_response.status_code, 204)
        self.assertIn(
            reverse('athlete-manage-detail', args=[self.athlete1.pk]),
            edit_response.headers['HX-Redirect'],
        )
        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal('2250.00'))
        self.assertIn('Malzemeler: Kulüp Tişörtü x3', payment.notes)

    def test_equipment_crud_and_protected_delete(self):
        self.client.force_login(self.user)
        list_url = reverse('equipment-list')
        create_url = reverse('equipment-create')

        self.assertEqual(self.client.get(list_url).status_code, 200)
        response = self.client.post(create_url, {'name': 'Bone', 'price': '125.00'})
        self.assertRedirects(response, list_url)

        equipment = Equipment.objects.get(name='Bone')
        response = self.client.post(
            reverse('equipment-update', args=[equipment.pk]),
            {'name': 'Silikon Bone', 'price': '150.00'},
        )
        self.assertRedirects(response, list_url)
        equipment.refresh_from_db()
        self.assertEqual(equipment.name, 'Silikon Bone')

        response = self.client.post(reverse('equipment-delete', args=[equipment.pk]))
        self.assertRedirects(response, list_url)
        self.assertFalse(Equipment.objects.filter(pk=equipment.pk).exists())

        sale_equipment = Equipment.objects.create(name='Forma', price=Decimal('500.00'))
        payment = PaymentRecord.objects.create(
            athlete=self.athlete1,
            payment_type='equipment_sale',
            period='2026-09',
            amount=Decimal('500.00'),
            status='paid',
            due_date=date.today(),
        )
        EquipmentSaleItem.objects.create(
            payment=payment,
            equipment=sale_equipment,
            quantity=1,
            unit_price=sale_equipment.price,
        )
        response = self.client.post(reverse('equipment-delete', args=[sale_equipment.pk]))
        self.assertRedirects(response, list_url)
        self.assertTrue(Equipment.objects.filter(pk=sale_equipment.pk).exists())

    def test_get_or_create_monthly_payments(self):
        period = "2026-08"
        payments = get_or_create_monthly_payments(period)
        
        # Should return annotated athletes without creating records
        self.assertEqual(len(payments), 2)

        p1 = next(item for item in payments if item.id == self.athlete1.id)
        p2 = next(item for item in payments if item.id == self.athlete2.id)

        self.assertEqual(p1.amount, Decimal('1500.00'))
        self.assertEqual(p2.amount, Decimal('1000.00'))
        self.assertEqual(p1.payment_status, 'pending')
        self.assertEqual(p2.payment_status, 'pending')
        self.assertIsNone(p1.payment_record)
        self.assertIsNone(p2.payment_record)
        self.assertEqual(PaymentRecord.objects.filter(period=period, payment_type='fee').count(), 0)
        
        # Calling function again should still not create database rows
        payments_again = get_or_create_monthly_payments(period)
        self.assertEqual(len(payments_again), 2)
        self.assertEqual(PaymentRecord.objects.filter(period=period, payment_type='fee').count(), 0)

    def test_get_financial_summary(self):
        period = "2026-08"
        PaymentRecord.objects.create(
            athlete=self.athlete1,
            period=period,
            amount=Decimal('1500.00'),
            status='paid',
            due_date=date(2026, 8, 15),
            collected_by=self.user,
            payment_type='fee'
        )
        
        # Create an expense
        Expense.objects.create(
            category=self.category,
            amount=Decimal('500.00'),
            expense_date=date(2026, 8, 5),
            period=period,
            created_by=self.user
        )

        summary = get_financial_summary(period)
        
        self.assertEqual(summary['period'], period)
        self.assertEqual(summary['total_income'], Decimal('1500.00'))
        self.assertEqual(summary['pending_income'], Decimal('1000.00'))
        self.assertEqual(summary['total_expense'], Decimal('500.00'))
        self.assertEqual(summary['net_balance'], 1000.00) # 1500 - 500 = 1000

    def test_team_fee_history_is_resolved_for_payment_period(self):
        current_fee = TeamFeeHistory.objects.get(team=self.team)
        current_fee.end_date = date(2026, 8, 31)
        current_fee.save(update_fields=['end_date'])
        TeamFeeHistory.objects.create(
            team=self.team,
            monthly_fee=Decimal('1800.00'),
            start_date=date(2026, 9, 1),
        )

        self.assertEqual(
            get_athlete_fee_for_period(self.athlete1, '2026-08'),
            Decimal('1500.00'),
        )
        self.assertEqual(
            get_athlete_fee_for_period(self.athlete1, '2026-09'),
            Decimal('1800.00'),
        )
