from django.db import models


class ScrapeRun(models.Model):
    class JobType(models.TextChoices):
        RESOLVE_DRAW = "resolve_draw", "Resolve Draw"
        SCRAPE_RESULTS = "scrape_results", "Scrape Results"
        VALIDATE_RESULTS = "validate_results", "Validate Results"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial"

    source = models.ForeignKey(
        "sources.LotterySource",
        on_delete=models.CASCADE,
        related_name="scrape_runs",
    )
    draw_event = models.ForeignKey(
        "draws.DrawEvent",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="scrape_runs",
    )
    job_type = models.CharField(max_length=30, choices=JobType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.STARTED,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    message = models.TextField(blank=True)
    error_details = models.TextField(blank=True)
    raw_snapshot_path = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source.code}:{self.job_type}:{self.status}"
