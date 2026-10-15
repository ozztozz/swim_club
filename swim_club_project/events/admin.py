from django.contrib import admin

from .models import CompetitionEvent, EventAttachment


class EventAttachmentInline(admin.TabularInline):
    model = EventAttachment
    extra = 1


@admin.register(CompetitionEvent)
class CompetitionEventAdmin(admin.ModelAdmin):
    list_display = ("event_date", "name", "pool_type", "age_group_start", "age_group_end", "place")
    list_filter = ("pool_type",)
    search_fields = ("name", "age_group_start", "age_group_end", "place")
    ordering = ("-event_date", "name")
    inlines = (EventAttachmentInline,)


@admin.register(EventAttachment)
class EventAttachmentAdmin(admin.ModelAdmin):
    list_display = ("event", "file", "uploaded_at")
    search_fields = ("event__name", "file")
