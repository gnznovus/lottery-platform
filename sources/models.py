from django.db import models


class LotterySource(models.Model):
    class Category(models.TextChoices):
        GOVERNMENT = "government", "Government"
        STOCK = "stock", "Stock"
        REGIONAL = "regional", "Regional"
        SPECIAL = "special", "Special"
        OTHER = "other", "Other"

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100, blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    timezone = models.CharField(max_length=64, default="Asia/Bangkok")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class SourceSchedule(models.Model):
    class ScheduleType(models.TextChoices):
        WEEKLY_DAYS = "weekly_days", "Weekly Days"
        MONTHLY_FIXED_DATES = "monthly_fixed_dates", "Monthly Fixed Dates"
        MANUAL = "manual", "Manual"
        CUSTOM = "custom", "Custom"

    source = models.ForeignKey(
        LotterySource,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    name = models.CharField(max_length=100, default="default")
    schedule_type = models.CharField(
        max_length=30,
        choices=ScheduleType.choices,
    )
    schedule_config = models.JSONField(default=dict, blank=True)
    requires_resolution = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source__code", "name"]
        unique_together = [("source", "name")]

    def __str__(self):
        return f"{self.source.code}:{self.name}"
