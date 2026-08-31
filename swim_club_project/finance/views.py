from django.shortcuts import render

# Create your views here.
# finance/views.py
from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import PaymentRecord
from .forms import ProcessPaymentForm
from .services import get_or_create_monthly_payments, get_financial_summary
from athletes.models import Team, Athlete
from .models import TeamFeeHistory, AthleteFeeHistory
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date

@login_required
def finance_dashboard(request):
    # Seçilen veya varsayılan dönem (YYYY-MM)
    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    
    # 1. Aidat borç kayıtları
    payments = get_or_create_monthly_payments(period)
    
    # 2. Özet veriler (Gelir, Bekleyen, Harcama, Net)
    financial_summary = get_financial_summary(period)
    
    context = {
        'period': period,
        'payments': payments,
        'financial_summary': financial_summary,
    }
    return render(request, 'finance/dashboard.html', context)

@login_required
def mark_payment_paid_htmx(request, pk):
    payment = get_object_or_404(PaymentRecord, pk=pk)

    if request.method == 'POST':
        form = ProcessPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.status = 'paid'
            payment.paid_at = timezone.now()
            payment.collected_by = request.user
            payment.save()

            
            # Güncellenmiş ödeme satırını ve trigger başlığını döndür
            period = payment.period
            financial_summary = get_financial_summary(period)
            response = render(request, 'finance/partials/_payment_row.html', {
                'payment': payment,
                'financial_summary': financial_summary,
                'period': period
            })
            response['HX-Trigger'] = 'closeModal, updateFinancialSummary'
            return response
    else:
        form = ProcessPaymentForm(instance=payment)

    return render(request, 'finance/modals/_mark_paid_modal.html', {
        'payment': payment,
        'form': form
    })



@login_required
def fee_management(request):
    """Takım ve Sporcu Ücret Yönetim Ana Sayfası"""
    teams = Team.objects.all().prefetch_related('fee_histories')
    athletes = Athlete.objects.filter(status='approved', is_active=True).prefetch_related('fee_histories')

    context = {
        'teams': teams,
        'athletes': athletes,
        'today': date.today(),
    }
    return render(request, 'finance/fee_management.html', context)


@login_required
def update_team_fee(request, team_id):
    """Takım Aidat Güncelleme (Eski kaydı kapatır, yeni kaydı başlatır)"""
    if request.method == 'POST':
        team = get_object_or_404(Team, id=team_id)
        new_fee = request.POST.get('monthly_fee')
        start_date_str = request.POST.get('start_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date.today()

        # 1. Takımın mevcut açık (end_date'i null olan) tarifesinin end_date'ini güncelle
        active_fee = TeamFeeHistory.objects.filter(team=team, end_date__isnull=True).first()
        if active_fee:
            # Yeni başlangıç tarihinden 1 gün öncesini bitiş tarihi yapıyoruz
            active_fee.end_date = start_date
            active_fee.save()

        # 2. Yeni tarife kaydı oluştur
        TeamFeeHistory.objects.create(
            team=team,
            monthly_fee=new_fee,
            start_date=start_date
        )

        messages.success(request, f"{team.name} için yeni aidat tarifesi kaydedildi.")
        return redirect('fee-management')


@login_required
def add_athlete_custom_fee(request, athlete_id):
    """Sporcuya Özel Fiyat/İndirim Ekleme"""
    if request.method == 'POST':
        athlete = get_object_or_404(Athlete, id=athlete_id)
        new_fee = request.POST.get('monthly_fee')
        start_date_str = request.POST.get('start_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date.today()

        # Aktif özel fiyat varsa kapat
        active_fee = AthleteFeeHistory.objects.filter(athlete=athlete, end_date__isnull=True).first()
        if active_fee:
            active_fee.end_date = start_date
            active_fee.save()

        AthleteFeeHistory.objects.create(
            athlete=athlete,
            monthly_fee=new_fee,
            start_date=start_date
        )

        messages.success(request, f"{athlete.get_full_name()} için özel fiyat tanımlandı.")
        return redirect('fee-management')