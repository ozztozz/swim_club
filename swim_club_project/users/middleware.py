import re

from django.shortcuts import redirect


class CoachScopeMiddleware:
    """Limit coaches to the dashboard and athletes assigned to their teams."""

    athlete_list_pattern = re.compile(r'^/athletes/manage/?$')
    athlete_detail_pattern = re.compile(r'^/athletes/manage/\d+/?$')
    distribution_pattern = re.compile(r'^/athletes/manage/\d+/equipment-sales/add/?$')
    training_attendance_pattern = re.compile(r'^/teams/attendance(?:/.*)?$')
    team_schedule_pattern = re.compile(r'^/teams/\d+/schedule/?$')
    team_list_pattern = re.compile(r'^/teams/?$')
    team_schedule_home_pattern = re.compile(r'^/teams/schedule/?$')
    team_detail_pattern = re.compile(r'^/teams/\d+/?$')
    auth_pattern = re.compile(r'^/(?:login|logout)/?$')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.rstrip('/') in {'/login', '/logout'}:
            return self.get_response(request)

        if request.user.is_authenticated and request.user.is_coach:
            path = request.path
            allowed = (
                path.startswith('/dashboard/')
                or self.athlete_list_pattern.match(path)
                or self.athlete_detail_pattern.match(path)
                or self.distribution_pattern.match(path)
                or self.training_attendance_pattern.match(path)
                or self.team_schedule_pattern.match(path)
                or self.team_list_pattern.match(path)
                or self.team_schedule_home_pattern.match(path)
                or self.team_detail_pattern.match(path)
                or self.auth_pattern.match(path)
            )
            if not allowed:
                return redirect('team-schedule-home')
        return self.get_response(request)
