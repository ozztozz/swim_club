from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from users.decorators import role_required
from .models import Athlete
from django.db.models import Q

@login_required
@role_required(allowed_roles=['admin', 'club_admin', 'coach'])
def dashboard_index(request):
    pending_athletes = Athlete.objects.filter(status='pending')
    approved_athletes = Athlete.objects.filter(status='approved')
    
    return render(request, 'dashboard/index.html', {
        'pending_athletes': pending_athletes,
        'approved_athletes': approved_athletes,
    })

@login_required
@role_required(allowed_roles=['admin', 'club_admin', 'coach'])
def search_approved_athletes_htmx(request):
    query = request.GET.get('q', '').strip()
    
    athletes = Athlete.objects.filter(status='approved')
    if query:
        athletes = athletes.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) |
            Q(parent__first_name__icontains=query) |
            Q(parent__last_name__icontains=query)
        )
        
    return render(request, 'dashboard/_approved_athletes.html', {'approved_athletes': athletes})


@login_required
@role_required(allowed_roles=['admin', 'club_admin', 'coach'])
@require_POST
def approve_athlete_htmx(request, pk):
    athlete = get_object_or_404(Athlete, pk=pk)
    athlete.status = 'approved'
    athlete.is_active = True
    athlete.save()
    
    # İşlem sonrası güncel listeyi HTMX'e parça HTML olarak döndürüyoruz
    pending_athletes = Athlete.objects.filter(status='pending')
    return render(request, 'dashboard/_pending_athletes.html', {'pending_athletes': pending_athletes})

@login_required
@role_required(allowed_roles=['admin', 'club_admin', 'coach'])
@require_POST
def reject_athlete_htmx(request, pk):
    athlete = get_object_or_404(Athlete, pk=pk)
    athlete.status = 'rejected'
    athlete.is_active = False
    athlete.save()
    
    pending_athletes = Athlete.objects.filter(status='pending')
    return render(request, 'dashboard/_pending_athletes.html', {'pending_athletes': pending_athletes})