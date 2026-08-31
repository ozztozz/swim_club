from django.shortcuts import render, get_object_or_404, redirect
from datetime import date
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from users.decorators import role_required
from .models import Athlete
from finance.services import get_or_create_monthly_payments, get_financial_summary
from finance.models import PaymentRecord
from teams.models import Team  # <-- Eklendi
from .forms import AthleteTeamForm
from django.db.models import Q

@login_required
@role_required(allowed_roles=['admin', 'club_admin', 'coach'])
def dashboard_index(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('parent-dashboard')  # Veli Dashboard
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

@login_required
@role_required(allowed_roles=['admin', 'club_admin', 'coach'])
def edit_athlete_team_htmx(request, pk):
    athlete = get_object_or_404(Athlete, pk=pk)

    if request.method == 'POST':
        form = AthleteTeamForm(request.POST, instance=athlete)
        if form.is_valid():
            form.save()
            approved_athletes = Athlete.objects.filter(status='approved')
            response = render(request, 'dashboard/_approved_athletes.html', {
                'approved_athletes': approved_athletes
            })
            response['HX-Trigger'] = 'closeModal'
            return response
    else:
        form = AthleteTeamForm(instance=athlete)

    # Şablon yolunu projedeki gerçek dosya adıyla güncelliyoruz:
    return render(request, 'dashboard/_edit_athlete_modal.html', {
        'athlete': athlete,
        'form': form
    })


@login_required
def parent_dashboard(request):
    # Giriş yapan velinin onaylı/onaysız çocukları
    children = Athlete.objects.filter(parent=request.user)
    
    # Çocukların tüm ödeme kayıtları
    payments = PaymentRecord.objects.filter(
        athlete__in=children
    ).select_related('athlete').order_by('-period')
    
    # Toplam bekleyen/gecikmiş borç
    pending_payments = payments.filter(status='pending')
    total_due = sum(p.amount for p in pending_payments)
    
    context = {
        'children': children,
        'payments': payments,
        'total_due': total_due,
        'has_pending': pending_payments.exists(),
    }
    return render(request, 'users_temps/parent_dashboard.html', context)
