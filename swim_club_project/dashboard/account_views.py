from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from datetime import date
from django.db.models import Sum, Count
from teams.models import Team
from finance.models import PaymentRecord




@login_required

def payment_status_list(request, payment_status):
    if payment_status not in {'paid', 'pending'}:
        return redirect('finance-dashboard')

    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    team_id = request.GET.get('team', '')
    monthly_payments = PaymentRecord.objects.filter(period=period,status=payment_status)
   # Toplam ödemeleri ve sporcu sayısını hesaplamak için her sporcunun toplam ödemesini alıyoruz.
    athletes_monthly_total = monthly_payments.values('athlete').annotate(
        athlete_total_amount=Sum('amount')
    )
    # Her sporcunun toplam ödemesini ve detaylarını bir sözlükte saklıyoruz.
    athlete_payments_list = []
    for athlete_total in athletes_monthly_total:
        athlete_payments = {}
        athlete_payments['athlete_id'] = athlete_total['athlete']
        athlete_payments['total_payment'] = athlete_total['athlete_total_amount']
        athlete_payments['last_payment_date'] = monthly_payments.filter(athlete=athlete_total['athlete']).order_by('-paid_at').first().paid_at if monthly_payments.filter(athlete=athlete_total['athlete']).exists() else None
        
        for payment in monthly_payments.filter(athlete=athlete_total['athlete']).order_by('-paid_at'):
            athlete_payments['name']= payment.athlete.get_full_name()
            athlete_payments['team'] = payment.athlete.team.name if payment.athlete.team else 'Takımsız'
            athlete_payments.setdefault('details', []).append({
                'amount': payment.amount,
                'date': payment.paid_at,
                
            })
        athlete_payments_list.append(athlete_payments)
    athlete_payments_list.sort(key=lambda x: x['last_payment_date'] , reverse=True)
    payments = monthly_payments
    total_amount = athletes_monthly_total.aggregate(total=Sum('athlete_total_amount'))['total'] or 0
    athlete_count = athletes_monthly_total.aggregate(count=Count('athlete', distinct=True))['count'] or 0

    teams = Team.objects.filter(is_active=True).order_by('name')

    return render(request, 'dashboard/payment_status_list.html', {
        'athlete_payments_list': athlete_payments_list,
        'period': period,
        'payments': payments,
        'total_amount': total_amount,
        'athlete_count': athlete_count,
        'payment_status': payment_status,
        'status_label': 'Ödeyen sporcular' if payment_status == 'paid' else 'Bekleyen sporcular',
        'teams': teams,
        'selected_team': team_id,
    })
