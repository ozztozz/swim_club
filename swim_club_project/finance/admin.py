# finance/admin.py
from django.contrib import admin
from .models import PaymentRecord, ExpenseCategory, Expense

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('athlete', 'period', 'amount', 'status', 'due_date', 'paid_at', 'collected_by')
    list_filter = ('period', 'status')
    search_fields = ('athlete__first_name', 'athlete__last_name', 'notes')
    ordering = ('-period', 'athlete__first_name')

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'amount', 'expense_date', 'period', 'receipt_no')
    list_filter = ('period', 'category')
    search_fields = ('title', 'receipt_no', 'notes')
    ordering = ('-expense_date',)