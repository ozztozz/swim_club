import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import GunlukBulten

@csrf_exempt
def bulten_kaydet_api(request):
    if request.method != 'POST':
        return JsonResponse({'hata': 'Yalnızca POST kabul edilir'}, status=405)
    
    try:
        data = json.loads(request.body)
        bulten = GunlukBulten.objects.create(
            baslik=data.get('baslik', 'Günlük Yüzme Antrenörü Bülteni'),
            icerik_json=data,
            icerik_html="", # NOT NULL kısıtlamasına takılmaması için boş bırakıyoruz
            aktif=data.get('aktif', True)
        )
        return JsonResponse({'durum': 'Basarili', 'id': bulten.id}, status=201)
    except Exception as e:
        return JsonResponse({'hata': str(e)}, status=400)