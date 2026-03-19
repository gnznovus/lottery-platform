from django.db import models


class DrawEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RESOLVED = "resolved", "Resolved"
        SHIFTED = "shifted", "Shifted"
        SCRAPED = "scraped", "Scraped"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        MANUAL_REVIEW = "manual_review", "Manual Review"

    class ResolutionMethod(models.TextChoices):
        SCHEDULE_RULE = "schedule_rule", "Schedule Rule"
        CALENDAR_SCRAPE = "calendar_scrape", "Calendar Scrape"
        MANUAL_OVERRIDE = "manual_override", "Manual Override"
        SYSTEM_INFERENCE = "system_inference", "System Inference"

    source = models.ForeignKey(
        "sources.LotterySource",
        on_delete=models.CASCADE,
        related_name="draw_events",
    )
    scheduled_date = models.DateField()
    resolved_date = models.DateField(blank=True, null=True)
    period_code = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    resolution_method = models.CharField(
        max_length=30,
        choices=ResolutionMethod.choices,
        blank=True,
    )
    resolution_source_url = models.URLField(blank=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    result_published_at = models.DateTimeField(blank=True, null=True)
    scraped_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_date", "source__code"]
        unique_together = [("source", "scheduled_date", "period_code")]

    def __str__(self):
        resolved = self.resolved_date or self.scheduled_date
        return f"{self.source.code}:{resolved}"
