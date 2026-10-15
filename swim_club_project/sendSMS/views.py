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