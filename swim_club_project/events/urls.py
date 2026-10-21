from django.urls import path

from . import views


urlpatterns = [
    path("", views.event_list, name="event-list"),
    path("bulk-match/", views.events_bulk_match, name="events-bulk-match"),
    path("bulk-match/select/", views.events_bulk_match_select, name="events-bulk-match-select"),
    path("new/", views.event_create, name="event-create"),
    path("<int:pk>/edit/", views.event_update, name="event-update"),
    path("<int:pk>/", views.event_detail, name="event-detail"),
    path("<int:pk>/attachments/add/", views.attachment_add, name="attachment-add"),
    path("<int:event_pk>/attachments/<int:attachment_pk>/delete/", views.attachment_delete, name="attachment-delete"),
]
