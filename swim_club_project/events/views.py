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