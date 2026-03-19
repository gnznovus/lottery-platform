from django.contrib import admin

from .models import DrawResult, RewardType


@admin.register(RewardType)
class RewardTypeAdmin(admin.ModelAdmin):
    list_display = ("source", "code", "name", "digit_length", "expected_count", "is_required", "sort_order")
    list_filter = ("source", "is_required")
    search_fields = ("source__code", "code", "name")
    ordering = ("source", "sort_order", "code")
    autocomplete_fields = ("source",)


@admin.register(DrawResult)
class DrawResultAdmin(admin.ModelAdmin):
    list_display = ("draw_event", "reward_type", "value", "sequence", "raw_label")
    list_filter = ("reward_type", "draw_event__source")
    search_fields = ("draw_event__source__code", "value", "raw_label")
    autocomplete_fields = ("draw_event", "reward_type")
