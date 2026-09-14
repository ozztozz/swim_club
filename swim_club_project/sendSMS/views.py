from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from finance.services import get_or_create_monthly_payments



def send_sms(request):
    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    team_id = request.GET.get('team', '')
    monthly_payments = get_or_create_monthly_payments(period)
    unpaid_athletes = [
        athlete for athlete in monthly_payments
        if (
            athlete.payment_status == 'pending'
            and athlete.parent_phone
            and getattr(athlete, 'regular_payment_day', None) is not None
            and athlete.regular_payment_day < date.today().day
        )
        and (not team_id or str(athlete.team_id) == team_id)
    ]

    return JsonResponse({
        'period': period,
        'count': len(unpaid_athletes),
        'athletes': [
            {
                'id': athlete.pk,
                'name': athlete.get_full_name(),
                'team': athlete.team.name if athlete.team_id else None,
                'parent_phone': athlete.parent_phone,
                'parent_email': athlete.parent_email,
                'amount': float(athlete.amount),
                'due_date': athlete.due_date.isoformat() if athlete.due_date else None,
                'is_overdue': athlete.due_date < date.today() if athlete.due_date else False,
                'payment_status': athlete.payment_status,
            }
            for athlete in unpaid_athletes
        ],
    })
