from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from draws.models import DrawEvent
from sources.models import LotterySource, SourceSchedule


WEEKDAY_MAP = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}


@dataclass
class ResolutionSummary:
    source_code: str
    schedule_name: str
    created: int = 0
    updated: int = 0


class ScheduleConfigError(ValueError):
    pass


def parse_iso_date(raw_value: str | None) -> date:
    if not raw_value:
        return timezone.localdate()
    return datetime.strptime(raw_value, "%Y-%m-%d").date()


def daterange(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def normalize_weekdays(days: list[str]) -> set[int]:
    normalized = set()
    for day in days:
        key = str(day).strip().lower()
        if key not in WEEKDAY_MAP:
            raise ScheduleConfigError(f"Unsupported weekday value: {day}")
        normalized.add(WEEKDAY_MAP[key])
    return normalized


def candidate_dates_for_schedule(schedule: SourceSchedule, start_date: date, end_date: date) -> list[date]:
    config = schedule.schedule_config or {}
    schedule_type = schedule.schedule_type
    matches = []

    if schedule_type == SourceSchedule.ScheduleType.WEEKLY_DAYS:
        weekdays = normalize_weekdays(config.get("days", []))
        if not weekdays:
            raise ScheduleConfigError("weekly_days schedule requires a non-empty 'days' list")
        for current in daterange(start_date, end_date):
            if current.weekday() in weekdays:
                matches.append(current)
        return matches

    if schedule_type == SourceSchedule.ScheduleType.MONTHLY_FIXED_DATES:
        days = {int(day) for day in config.get("days", [])}
        if not days:
            raise ScheduleConfigError("monthly_fixed_dates schedule requires a non-empty 'days' list")
        for current in daterange(start_date, end_date):
            if current.day in days:
                matches.append(current)
        return matches

    if schedule_type == SourceSchedule.ScheduleType.MANUAL:
        return []

    raise ScheduleConfigError(f"Unsupported schedule type: {schedule_type}")


@transaction.atomic
def sync_draw_events_for_schedule(schedule: SourceSchedule, start_date: date, end_date: date) -> ResolutionSummary:
    summary = ResolutionSummary(source_code=schedule.source.code, schedule_name=schedule.name)

    for scheduled_date in candidate_dates_for_schedule(schedule, start_date, end_date):
        defaults = {
            "status": DrawEvent.Status.PENDING,
            "notes": "Generated from schedule rule.",
        }

        if not schedule.requires_resolution:
            defaults.update(
                {
                    "resolved_date": scheduled_date,
                    "status": DrawEvent.Status.RESOLVED,
                    "resolution_method": DrawEvent.ResolutionMethod.SCHEDULE_RULE,
                    "resolved_at": timezone.now(),
                    "notes": "Resolved automatically from schedule rule.",
                }
            )

        draw_event, created = DrawEvent.objects.get_or_create(
            source=schedule.source,
            scheduled_date=scheduled_date,
            period_code="",
            defaults=defaults,
        )

        if created:
            summary.created += 1
            continue

        has_changed = False
        if not schedule.requires_resolution and draw_event.resolved_date != scheduled_date:
            draw_event.resolved_date = scheduled_date
            draw_event.resolution_method = DrawEvent.ResolutionMethod.SCHEDULE_RULE
            draw_event.status = DrawEvent.Status.RESOLVED
            draw_event.resolved_at = timezone.now()
            draw_event.notes = "Resolved automatically from schedule rule."
            has_changed = True

        if schedule.requires_resolution and draw_event.status == DrawEvent.Status.FAILED:
            draw_event.status = DrawEvent.Status.PENDING
            draw_event.notes = "Reset to pending by schedule sync."
            has_changed = True

        if has_changed:
            draw_event.save()
            summary.updated += 1

    return summary


@transaction.atomic
def sync_draw_events(
    source: LotterySource | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ResolutionSummary]:
    start_date = start_date or timezone.localdate()
    end_date = end_date or start_date

    schedules = SourceSchedule.objects.select_related("source").filter(is_active=True, source__is_active=True)
    if source is not None:
        schedules = schedules.filter(source=source)

    summaries = []
    for schedule in schedules:
        summaries.append(sync_draw_events_for_schedule(schedule, start_date, end_date))
    return summaries
