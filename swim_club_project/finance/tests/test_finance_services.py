from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from teams.models import Team
from athletes.models import Athlete
from finance.models import PaymentRecord, ExpenseCategory, Expense
from finance.services import get_or_create_monthly_payments, get_financial_summary

User = get_user_model()

class FinanceModelAndServiceTests(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='adminuser',
            password='password123',
            role='admin'
        )
        
        # Create Team
        self.team = Team.objects.create(
            name="A Takımı",
            monthly_fee=Decimal('1500.00'),
            is_active=True
        )
        
        # Create Approved Athletes
        self.athlete1 = Athlete.objects.create(
            first_name="Ahmet",
            last_name="Yılmaz",
            birth_date=date(2012, 5, 10),
            gender="M",
            status="approved",
            team=self.team
        )
        self.athlete2 = Athlete.objects.create(
            first_name="Ayşe",
            last_name="Kaya",
            birth_date=date(2013, 8, 20),
            gender="F",
            status="approved",
            team=self.team,
            custom_fee=Decimal('1000.00')  # Özel burslu/aidatlı
        )
        # Pending athlete (should not get payment record)
        self.athlete_pending = Athlete.objects.create(
            first_name="Mehmet",
            last_name="Demir",
            birth_date=date(2014, 1, 15),
            gender="M",
            status="pending"
        )
        
        # Create Expense Category
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

    def test_get_or_create_monthly_payments(self):
        period = "2026-08"
        payments = get_or_create_monthly_payments(period)
        
        # Should create records for 2 approved athletes only
        self.assertEqual(payments.count(), 2)
        
        p1 = PaymentRecord.objects.get(athlete=self.athlete1, period=period)
        p2 = PaymentRecord.objects.get(athlete=self.athlete2, period=period)
        
        self.assertEqual(p1.amount, Decimal('1500.00'))
        self.assertEqual(p2.amount, Decimal('1000.00'))
        
        # Calling function again should not create duplicate records (Idempotency check)
        payments_again = get_or_create_monthly_payments(period)
        self.assertEqual(payments_again.count(), 2)

    def test_get_financial_summary(self):
        period = "2026-08"
        get_or_create_monthly_payments(period)
        
        # Mark athlete1 payment as paid
        p1 = PaymentRecord.objects.get(athlete=self.athlete1, period=period)
        p1.status = 'paid'
        p1.collected_by = self.user
        p1.save()
        
        # Create an expense
        Expense.objects.create(
            title="Ağustos Havuz Kirası",
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
