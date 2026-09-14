from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from finance.services import get_or_create_monthly_payments

from .services import IletiMerkeziService


SMS_MESSAGE_TEMPLATE = (
    'Sayın velimiz, sporcumuz {athlete_name} {period} '
    'aidatı ({amount} TL) ödenmemiş görünmektedir. Ödeme yaptıysanız '
    'bu mesajı dikkate almayınız. Alpha Academy'
)


def build_unpaid_payment_message(athlete, period):
    return SMS_MESSAGE_TEMPLATE.format(
        athlete_name=athlete.get_full_name(),
        period=period,
        amount=f'{athlete.amount:.2f}',
    )



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
            and athlete.regular_payment_day +3 < date.today().day
        )
        and (not team_id or str(athlete.team_id) == team_id)
    ]
    

    athletes = []
    for athlete in unpaid_athletes:
        message = build_unpaid_payment_message(athlete, period)
        sms_result = IletiMerkeziService.send_sms(athlete.parent_phone, message)
        athlete_data = {
            'id': athlete.pk,
            'name': athlete.get_full_name(),
            'team': athlete.team.name if athlete.team_id else None,
            'parent_phone': "5302442670",
            'parent_email': athlete.parent_email,
            'amount': float(athlete.amount),
            'regular_payment_day': athlete.regular_payment_day,
            'is_overdue': athlete.regular_payment_day < date.today().day,
            'payment_status': athlete.payment_status,
            'message': message,
            'sms_status': sms_result.get('status'),
        }
        if sms_result.get('status') == 'success':
            athlete_data['sms_id'] = sms_result.get('id')
        else:
            athlete_data['sms_error'] = sms_result.get('message', 'SMS gönderilemedi.')
        athletes.append(athlete_data)

    return JsonResponse({
        'period': period,
        'count': len(unpaid_athletes),
        'message_template': SMS_MESSAGE_TEMPLATE,
        'athletes': athletes,
    })
