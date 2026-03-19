from datetime import date

from django.test import TestCase

from draws.models import DrawEvent
from draws.services import candidate_dates_for_schedule, sync_draw_events_for_schedule
from sources.models import LotterySource, SourceSchedule


class DrawScheduleServiceTests(TestCase):
    def setUp(self):
        self.source = LotterySource.objects.create(code="huayrat", name="Huay Rat")

    def test_weekly_schedule_candidates(self):
        schedule = SourceSchedule.objects.create(
            source=self.source,
            name="weekly",
            schedule_type=SourceSchedule.ScheduleType.WEEKLY_DAYS,
            schedule_config={"days": ["mon", "fri"]},
        )

        dates = candidate_dates_for_schedule(schedule, date(2026, 3, 16), date(2026, 3, 22))

        self.assertEqual(dates, [date(2026, 3, 16), date(2026, 3, 20)])

    def test_monthly_schedule_candidates(self):
        schedule = SourceSchedule.objects.create(
            source=self.source,
            name="monthly",
            schedule_type=SourceSchedule.ScheduleType.MONTHLY_FIXED_DATES,
            schedule_config={"days": [1, 16]},
        )

        dates = candidate_dates_for_schedule(schedule, date(2026, 3, 1), date(2026, 3, 20))

        self.assertEqual(dates, [date(2026, 3, 1), date(2026, 3, 16)])

    def test_sync_resolves_non_drifting_schedule_immediately(self):
        schedule = SourceSchedule.objects.create(
            source=self.source,
            name="weekly",
            schedule_type=SourceSchedule.ScheduleType.WEEKLY_DAYS,
            schedule_config={"days": ["fri"]},
            requires_resolution=False,
        )

        summary = sync_draw_events_for_schedule(schedule, date(2026, 3, 20), date(2026, 3, 20))
        draw_event = DrawEvent.objects.get(source=self.source, scheduled_date=date(2026, 3, 20))

        self.assertEqual(summary.created, 1)
        self.assertEqual(draw_event.resolved_date, date(2026, 3, 20))
        self.assertEqual(draw_event.status, DrawEvent.Status.RESOLVED)
        self.assertEqual(draw_event.resolution_method, DrawEvent.ResolutionMethod.SCHEDULE_RULE)

    def test_sync_leaves_drifting_schedule_pending(self):
        schedule = SourceSchedule.objects.create(
            source=self.source,
            name="monthly",
            schedule_type=SourceSchedule.ScheduleType.MONTHLY_FIXED_DATES,
            schedule_config={"days": [1, 16]},
            requires_resolution=True,
        )

        summary = sync_draw_events_for_schedule(schedule, date(2026, 3, 16), date(2026, 3, 16))
        draw_event = DrawEvent.objects.get(source=self.source, scheduled_date=date(2026, 3, 16))

        self.assertEqual(summary.created, 1)
        self.assertIsNone(draw_event.resolved_date)
        self.assertEqual(draw_event.status, DrawEvent.Status.PENDING)
