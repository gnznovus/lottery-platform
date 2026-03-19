from django.contrib import admin

from .models import LotterySource, SourceSchedule


class SourceScheduleInline(admin.TabularInline):
    model = SourceSchedule
    extra = 0
    fields = ("name", "schedule_type", "requires_resolution", "is_active")
    show_change_link = True


@admin.register(LotterySource)
class LotterySourceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "country", "timezone", "is_active", "updated_at")
    list_filter = ("category", "country", "is_active")
    search_fields = ("code", "name")
    ordering = ("code",)
    inlines = [SourceScheduleInline]


@admin.register(SourceSchedule)
class SourceScheduleAdmin(admin.ModelAdmin):
    list_display = ("source", "name", "schedule_type", "requires_resolution", "is_active", "updated_at")
    list_filter = ("schedule_type", "requires_resolution", "is_active")
    search_fields = ("source__code", "source__name", "name")
    autocomplete_fields = ("source",)
