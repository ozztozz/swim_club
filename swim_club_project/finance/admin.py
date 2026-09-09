# finance/admin.py
from django.contrib import admin
from .models import Equipment, EquipmentSaleItem, PaymentRecord, ExpenseCategory, Expense,RegularExpense,TeamFeeHistory


class EquipmentSaleItemInline(admin.TabularInline):
    model = EquipmentSaleItem
    extra = 0


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ('athlete', 'payment_type', 'period', 'amount', 'status', 'due_date', 'paid_at', 'collected_by')
    list_filter = ('payment_type', 'period', 'status')
    search_fields = ('athlete__first_name', 'athlete__last_name', 'notes')
    ordering = ('-period', 'athlete__first_name')
    inlines = (EquipmentSaleItemInline,)

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

    list_editable = ('description',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('reciever', 'category', 'amount', 'expense_date', 'period', 'receipt_no')
    list_filter = ('period', 'category')
    search_fields = ('title', 'receipt_no', 'notes')
    ordering = ('-expense_date',)

@admin.register(RegularExpense)
class RegularExpenseAdmin(admin.ModelAdmin):
    list_display = ('reciever', 'category', 'amount', 'paymentDay', 'start_date', 'end_date')
    list_filter = ('paymentDay', 'category')
    search_fields = ('reciever', 'notes')
    ordering = ('-paymentDay',)

@admin.register(TeamFeeHistory)
class TeamFeeHistoryAdmin(admin.ModelAdmin):
    list_display = ('team', 'monthly_fee', 'start_date', 'end_date')
