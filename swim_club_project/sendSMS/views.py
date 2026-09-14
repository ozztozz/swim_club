from django.http import JsonResponse

from .services import get_sms_service

def send_sms(request):
   
    
    return JsonResponse({
            "message": "SMS başarıyla sıraya alındı.", 
            "sms": "result",
        })
