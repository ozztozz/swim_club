from django.http import JsonResponse

from .services import get_sms_service

def send_sms(request):
    # Kendi telefon numaranızı yazarak test edin
    test_phone = "5054152225" 
    sms_text = "SLM"
    
    result = get_sms_service().send(test_phone, sms_text)
    
    if result.get("status") != "error":
        return JsonResponse({
            "message": "SMS başarıyla sıraya alındı.", 
            "sms": result,
        })
    else:
        return JsonResponse({
            "error": "SMS gönderimi başarısız oldu.", 
            "details": result
        }, status=400)
