from django.contrib import admin

from .models import ScrapeRun


@admin.register(ScrapeRun)
class ScrapeRunAdmin(admin.ModelAdmin):
    list_display = ("source", "job_type", "status", "draw_event", "started_at", "finished_at", "message_preview")
    list_filter = ("job_type", "status", "source")
    search_fields = ("source__code", "message", "error_details")
    date_hierarchy = "started_at"
    autocomplete_fields = ("source", "draw_event")
    readonly_fields = ("started_at", "finished_at", "message", "error_details", "raw_snapshot_path", "metadata")

    @admin.display(description="Message")
    def message_preview(self, obj):
        return (obj.message or "")[:80]
