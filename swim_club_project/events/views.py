from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from django.forms import modelformset_factory
from .forms import CompetitionEventForm, EventAttachmentForm


from .models import CompetitionEvent, EventAttachment


AttachmentFormSet = modelformset_factory(
    EventAttachment,
    form=EventAttachmentForm,
    extra=1,
)


def _can_manage_events(user):
    return user.is_authenticated and (user.is_superuser or user.is_club_admin)


@login_required
def event_list(request):
    return render(request, "events/event_list.html", _event_list_context(request))


def _event_list_context(request):
    query = request.GET.get("q", "").strip()
    events = CompetitionEvent.objects.all()
    if query:
        events = events.filter(
            Q(name__icontains=query)
            | Q(age_group_start__icontains=query)
            | Q(age_group_end__icontains=query)
            | Q(place__icontains=query)
        )
    return {
        "events": events,
        "query": query,
        "can_manage": _can_manage_events(request.user),
    }


@login_required
def event_detail(request, pk):
    event = get_object_or_404(
        CompetitionEvent.objects.prefetch_related("attachments"),
        pk=pk,
    )
    formset = AttachmentFormSet(queryset=EventAttachment.objects.none())
    return render(request, "events/event_detail.html", {
        "event": event,
        "can_manage": _can_manage_events(request.user),
        "attachments_formset": formset,
    })


@login_required
def event_create(request):
    if not _can_manage_events(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = CompetitionEventForm(request.POST)
        attachments_formset = AttachmentFormSet(request.POST, request.FILES)
        if form.is_valid() and attachments_formset.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            for attachment_form in attachments_formset:
                if attachment_form.cleaned_data:
                    EventAttachment.objects.create(
                        event=event,
                        file=attachment_form.cleaned_data["file"],
                        file_name=attachment_form.cleaned_data["file_name"],
                    )
            messages.success(request, "Yarışma / etkinlik kaydedildi.")
            if request.headers.get("HX-Request") == "true":
                response = render(
                    request,
                    "events/partials/_event_list.html",
                    _event_list_context(request),
                )
                response["HX-Trigger"] = "closeModal"
                return response
            return redirect("event-detail", pk=event.pk)
    else:
        form = CompetitionEventForm()
        attachments_formset = AttachmentFormSet(queryset=EventAttachment.objects.none())

    template = (
        "events/partials/event_form_modal.html"
        if request.headers.get("HX-Request") == "true"
        else "events/event_form.html"
    )
    return render(request, template, {
        "form": form,
        "attachments_formset": attachments_formset,
        "title": "Yarışma / etkinlik ekle",
        "form_action": "event-create",
    })

@login_required
def event_update(request, pk):
    if not _can_manage_events(request.user):
        raise PermissionDenied

    event = get_object_or_404(CompetitionEvent, pk=pk)
    if request.method == "POST":
        form = CompetitionEventForm(request.POST, instance=event)
        attachments_form = EventAttachmentsForm(request.POST, request.FILES)
        if form.is_valid() and attachments_form.is_valid():
            form.save()
            for uploaded_file in attachments_form.cleaned_data["files"]:
                EventAttachment.objects.create(event=event, file=uploaded_file)
            messages.success(request, "Yarışma / etkinlik güncellendi.")
            if request.headers.get("HX-Request") == "true":
                response = render(
                    request,
                    "events/partials/_event_list.html",
                    _event_list_context(request),
                )
                response["HX-Trigger"] = "closeModal"
                return response
            return redirect("event-detail", pk=event.pk)
    else:
        form = CompetitionEventForm(instance=event)


    template = (
        "events/partials/event_form_modal.html"
        if request.headers.get("HX-Request") == "true"
        else "events/event_form.html"
    )
    return render(request, template, {
        "form": form,
        "title": "Yarışma / etkinlik düzenle",
        "form_action": "event-update",
        "event": event,
    })


def attachment_add(request, pk):
    if not _can_manage_events(request.user):
        raise PermissionDenied
    
    event = get_object_or_404(CompetitionEvent, pk=pk)
    
    # Her seferinde ekrana 3 tane boş satır getirelim
    AttachmentFormSet = modelformset_factory(
        EventAttachment,
        form=EventAttachmentForm,
        extra=3,
        can_delete=True
    )
    
    if request.method == "POST":
        formset = AttachmentFormSet(request.POST, request.FILES, queryset=EventAttachment.objects.none())
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.event = event
                instance.save()
            messages.success(request, "Dosyalar başarıyla eklendi.")
            return redirect("event-detail", pk=event.pk)
    else:
        formset = AttachmentFormSet(queryset=EventAttachment.objects.none())

    return render(request, "events/partials/attachment_form_modal.html", {
        "attachments_formset": formset,
        "event": event,
    })
    if not _can_manage_events(request.user):
        raise PermissionDenied
    
    event = get_object_or_404(CompetitionEvent, pk=pk)
    
    # EventAttachment modeli için formset oluşturuyoruz (varsayılan olarak 3 boş satır ile başlar)
    AttachmentFormSet = modelformset_factory(
        EventAttachment,
        form=EventAttachmentsForm,
        extra=3,
        can_delete=True
    )
    
    if request.method == "POST":
        formset = AttachmentFormSet(request.POST, request.FILES, queryset=EventAttachment.objects.none())
        if formset.is_valid():
            attachments = formset.save(commit=False)
            for attachment in attachments:
                attachment.event = event
                attachment.save()
            
            messages.success(request, "Dosyalar başarıyla eklendi.")
            return redirect("event-detail", pk=event.pk)
    else:
        formset = AttachmentFormSet(queryset=EventAttachment.objects.none())

    return render(request, "events/partials/attachment_form_modal.html", {
        "attachments_formset": formset,
        "event": event,
    })

def attachment_delete(request, event_pk, attachment_pk):
    if not _can_manage_events(request.user):
        raise PermissionDenied
    
    attachment = get_object_or_404(EventAttachment, pk=attachment_pk)
    attachment.delete()
    messages.success(request, "Dosya başarıyla silindi.")
    return redirect("event-detail", pk=event_pk)

@login_required
def events_bulk_match(request):
    """Aktif sporcuları topluca tarar, tam eşleşenleri otomatik bağlar, benzerleri listeler."""
    if not (request.user.is_superuser or request.user.is_club_admin or getattr(request.user, 'is_coach', False)):
        raise PermissionDenied

    from athletes.models import Athlete

    all_active = Athlete.objects.filter(is_active=True).order_by('first_name', 'last_name')
    total_active_count = all_active.count()
    already_matched = list(all_active.filter(external_swimmer_id__isnull=False))
    to_scan = list(all_active.filter(external_swimmer_id__isnull=True))

    run_scan = request.GET.get('run') == '1'

    if not run_scan:
        return render(request, 'events/partials/bulk_match_modal.html', {
            'mode': 'init',
            'total_active_count': total_active_count,
            'already_matched_count': len(already_matched),
            'to_scan_count': len(to_scan),
        })

    import json
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    auto_matched = []
    potential_matches = []
    unmatched = []

    def scan_one(athlete):
        api_url = 'https://ozztozz.pythonanywhere.com/api/sporcu-eslestir/'
        payload = {'sporcu_adi': athlete.get_full_name().strip()}
        if athlete.birth_date:
            payload['dogum_yili'] = athlete.birth_date.year
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            api_url,
            data=req_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 BulkMatch/1.0',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return athlete, data
        except Exception as exc:
            return athlete, {'durum': 'hata', 'mesaj': str(exc)}

    if to_scan:
        # PythonAnywhere için nazik worker sayısı (3 worker)
        with ThreadPoolExecutor(max_workers=3) as executor:
            scan_results = list(executor.map(scan_one, to_scan))

        for athlete, res in scan_results:
            sonuc = res.get('sonuc')
            if res.get('durum') == 'basarili' and sonuc == 'tam_eslesme':
                bulunan_id = res.get('bulunan_id') or (res.get('sporcu') or {}).get('id')
                if bulunan_id:
                    try:
                        athlete.external_swimmer_id = int(bulunan_id)
                        athlete.save(update_fields=['external_swimmer_id'])
                        auto_matched.append({
                            'athlete': athlete,
                            'db_id': bulunan_id,
                            'sporcu': res.get('sporcu') or {},
                        })
                    except Exception:
                        unmatched.append(athlete)
                else:
                    unmatched.append(athlete)
            elif res.get('muhtemel_eslesmeler'):
                potential_matches.append({
                    'athlete': athlete,
                    'candidates': res.get('muhtemel_eslesmeler', []),
                })
            else:
                unmatched.append(athlete)

    context = {
        'mode': 'results',
        'total_active_count': total_active_count,
        'already_matched_count': len(already_matched),
        'auto_matched': auto_matched,
        'auto_matched_count': len(auto_matched),
        'potential_matches': potential_matches,
        'potential_matches_count': len(potential_matches),
        'unmatched': unmatched,
        'unmatched_count': len(unmatched),
    }

    if request.headers.get('HX-Request') and request.GET.get('run') == '1':
        return render(request, 'events/partials/bulk_match_results_inner.html', context)
    return render(request, 'events/partials/bulk_match_modal.html', context)


@login_required
def events_bulk_match_select(request):
    """Benzer eşleşmeler listesinden tek bir adayın seçilip kaydedilmesi (inline HTMX)."""
    if not (request.user.is_superuser or request.user.is_club_admin or getattr(request.user, 'is_coach', False)):
        raise PermissionDenied

    from athletes.models import Athlete
    from django.http import HttpResponse

    athlete_id = request.POST.get('athlete_id')
    swimmer_id = request.POST.get('swimmer_id')
    swimmer_name = request.POST.get('swimmer_name', '')

    athlete = get_object_or_404(Athlete, pk=athlete_id)
    clean_id = str(swimmer_id).replace('.', '').replace(',', '').strip() if swimmer_id else ''
    if clean_id.isdigit():
        athlete.external_swimmer_id = int(clean_id)
        athlete.save(update_fields=['external_swimmer_id'])
        return render(request, 'events/partials/bulk_match_row_selected.html', {
            'athlete': athlete,
            'swimmer_id': clean_id,
            'swimmer_name': swimmer_name,
        })
    return HttpResponse('Geçersiz ID', status=400)
