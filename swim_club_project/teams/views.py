from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import TeamForm
from .models import Team


def _team_context(request):
	query = request.GET.get('q', '').strip()
	status = request.GET.get('status', 'active')
	teams = Team.objects.prefetch_related('coaches').order_by('name')

	if query:
		teams = teams.filter(name__icontains=query)
	if status == 'active':
		teams = teams.filter(is_active=True)
	elif status == 'inactive':
		teams = teams.filter(is_active=False)

	return {
		'teams': teams,
		'query': query,
		'status': status,
	}


@login_required
def team_list(request):
	return render(request, 'team/team_list.html', _team_context(request))


@login_required
def team_detail(request, pk):
	team = get_object_or_404(
		Team.objects.prefetch_related('coaches', 'athletes'),
		pk=pk,
	)
	return render(request, 'team/team_detail.html', {'team': team})


@login_required
def team_create(request):
	form = TeamForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		form.save()
		response = render(request, 'team/partials/team_table.html', _team_context(request))
		response['HX-Trigger'] = 'closeTeamModal'
		return response

	return render(request, 'team/partials/team_form_modal.html', {
		'form': form,
		'modal_title': 'Yeni takım ekle',
		'submit_label': 'Takımı kaydet',
		'form_url': 'team-create',
	})


@login_required
def team_update(request, pk):
	team = get_object_or_404(Team, pk=pk)
	form = TeamForm(request.POST or None, instance=team)
	return_to_detail = request.GET.get('return_to_detail') or request.POST.get('return_to_detail')
	if request.method == 'POST' and form.is_valid():
		form.save()
		if return_to_detail:
			response = render(request, 'team/team_detail.html', {'team': team})
			response['HX-Redirect'] = request.build_absolute_uri(reverse('team-detail', args=[team.pk]))
			return response
		response = render(request, 'team/partials/team_table.html', _team_context(request))
		response['HX-Trigger'] = 'closeTeamModal'
		return response

	return render(request, 'team/partials/team_form_modal.html', {
		'form': form,
		'team': team,
		'modal_title': 'Takımı düzenle',
		'submit_label': 'Değişiklikleri kaydet',
		'form_url': 'team-update',
		'return_to_detail': return_to_detail,
	})


@login_required
def team_delete(request, pk):
	team = get_object_or_404(Team, pk=pk)
	if request.method == 'POST':
		team.delete()
		response = render(request, 'team/partials/team_table.html', _team_context(request))
		response['HX-Trigger'] = 'closeTeamModal'
		return response

	return render(request, 'team/partials/team_delete_modal.html', {'team': team})

