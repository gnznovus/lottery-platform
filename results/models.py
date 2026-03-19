from django.db import models


class RewardType(models.Model):
    source = models.ForeignKey(
        "sources.LotterySource",
        on_delete=models.CASCADE,
        related_name="reward_types",
    )
    code = models.SlugField(max_length=50)
    name = models.CharField(max_length=255)
    digit_length = models.PositiveSmallIntegerField(blank=True, null=True)
    expected_count = models.PositiveSmallIntegerField(blank=True, null=True)
    is_required = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source__code", "sort_order", "code"]
        unique_together = [("source", "code")]

    def __str__(self):
        return f"{self.source.code}:{self.code}"


class DrawResult(models.Model):
    draw_event = models.ForeignKey(
        "draws.DrawEvent",
        on_delete=models.CASCADE,
        related_name="results",
    )
    reward_type = models.ForeignKey(
        RewardType,
        on_delete=models.PROTECT,
        related_name="results",
    )
    value = models.CharField(max_length=100)
    sequence = models.PositiveSmallIntegerField(blank=True, null=True)
    raw_label = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["draw_event_id", "reward_type__sort_order", "sequence", "value"]
        unique_together = [("draw_event", "reward_type", "value", "sequence")]

    def __str__(self):
        return f"{self.draw_event} {self.reward_type.code}={self.value}"
