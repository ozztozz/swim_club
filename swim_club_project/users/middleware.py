import re

from django.core.exceptions import PermissionDenied


class CoachScopeMiddleware:
    """Limit coaches to the dashboard and athletes assigned to their teams."""

    athlete_list_pattern = re.compile(r'^/athletes/manage/?$')
    athlete_detail_pattern = re.compile(r'^/athletes/manage/\d+/?$')
    distribution_pattern = re.compile(r'^/athletes/manage/\d+/equipment-sales/add/?$')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_coach:
            path = request.path
            allowed = (
                path.startswith('/dashboard/')
                or self.athlete_list_pattern.match(path)
                or self.athlete_detail_pattern.match(path)
                or self.distribution_pattern.match(path)
            )
            if not allowed:
                raise PermissionDenied
        return self.get_response(request)
