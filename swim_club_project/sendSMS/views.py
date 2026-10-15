from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

from finance.services import get_or_create_monthly_payments

from .services import IletiMerkeziService
from .models import GunlukBulten

SMS_TEST_PHONE = "905302442670"
SMS_RESEND_COOLDOWN_DAYS = 3


SMS_MESSAGE_TEMPLATE = (
    'Sayın velimiz, sporcumuz {athlete_name} {period} '
    'aidatı ({amount} TL) ödenmemiş görünmektedir. Ödeme yaptıysanız '
    'bu mesajı dikkate almayınız. Alpha Academy'
)


def build_unpaid_payment_message(athlete, period):
    return SMS_MESSAGE_TEMPLATE.format(
        athlete_name=athlete.get_full_name(),
        period=period,
        amount=f'{athlete.amount}',
    )



def send_sms(request):
    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    team_id = request.GET.get('team', '')
    monthly_payments = get_or_create_monthly_payments(period)
    cooldown_cutoff = timezone.now() - timedelta(days=SMS_RESEND_COOLDOWN_DAYS)
    unpaid_athletes = [
        athlete for athlete in monthly_payments
        if (
            athlete.payment_status == 'pending'
            and athlete.parent_phone
            and getattr(athlete, 'regular_payment_day', None) is not None
            and athlete.regular_payment_day +3 < date.today().day
            and (athlete.last_sms_time is None or athlete.last_sms_time < cooldown_cutoff)
        )
        and (not team_id or str(athlete.team_id) == team_id)
    ]
    

    athletes = []
    for athlete in unpaid_athletes:
        message = build_unpaid_payment_message(athlete, period)
        sms_result = IletiMerkeziService.send_sms(SMS_TEST_PHONE, message)
        athlete_data = {
            'id': athlete.pk,
            'name': athlete.get_full_name(),
            'team': athlete.team.name if athlete.team_id else None,
            'parent_phone': athlete.parent_phone,
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
            athlete.last_sms_time = timezone.now()
            athlete.save(update_fields=['last_sms_time'])
        else:
            athlete_data['sms_error'] = sms_result.get('message', 'SMS gönderilemedi.')
        athletes.append(athlete_data)

    return JsonResponse({
        'period': period,
        'count': len(unpaid_athletes),
        'message_template': SMS_MESSAGE_TEMPLATE,
        'athletes': athletes,
    })


# views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import GunlukBulten



@csrf_exempt
def bulten_kaydet_api(request):
    if request.method != 'POST':
        return JsonResponse({'hata': 'Yalnızca POST istekleri kabul edilir.'}, status=405)
    
    # Basit API anahtarı doğrulamas
    
    try:
        data = json.loads(request.body)
        bulten = GunlukBulten.objects.create(
            baslik=data.get('baslik', 'Günlük Yüzme Bülteni'),
            icerik_html=data.get('icerik')
        )
        return JsonResponse({'durum': 'Basarili', 'id': bulten.id}, status=201)
    except Exception as e:
        return JsonResponse({'hata': str(e)}, status=400)