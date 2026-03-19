from django.contrib import admin

from results.models import DrawResult

from .models import DrawEvent


class DrawResultInline(admin.TabularInline):
    model = DrawResult
    extra = 0
    fields = ("reward_type", "value", "sequence", "raw_label")
    readonly_fields = ("reward_type", "value", "sequence", "raw_label")
    can_delete = False
    show_change_link = True
    ordering = ("reward_type__sort_order", "sequence", "id")


@admin.register(DrawEvent)
class DrawEventAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "scheduled_date",
        "resolved_date",
        "status",
        "resolution_method",
        "period_code",
        "scraped_at",
        "completed_at",
    )
    list_filter = ("source", "status", "resolution_method")
    search_fields = ("source__code", "period_code", "notes")
    date_hierarchy = "scheduled_date"
    autocomplete_fields = ("source",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [DrawResultInline]
