from django.http import JsonResponse

from .services import IletiMerkeziService

def send_sms(request):
    result = IletiMerkeziService.send_sms(
        "5302442670",
        "SLM",
    )
    return JsonResponse({
            "message": result.get("status"),
            "sms_id": result.get("id"),
        })


    if result.get("status") == "success":
        return JsonResponse({
            "message": "SMS başarıyla sıraya alındı.",
            "sms_id": result.get("id"),
        })

    return JsonResponse({
        "error": "SMS gönderimi başarısız oldu.",
        "details": result,
    }, status=400)
