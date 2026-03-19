from django.core.management.base import BaseCommand, CommandError

from draws.services import parse_iso_date, sync_draw_events
from sources.models import LotterySource


class Command(BaseCommand):
    help = "Create or refresh DrawEvent rows from active source schedules."

    def add_arguments(self, parser):
        parser.add_argument("--source", dest="source_code", help="Optional source code filter")
        parser.add_argument("--start-date", dest="start_date", help="Start date in YYYY-MM-DD")
        parser.add_argument("--end-date", dest="end_date", help="End date in YYYY-MM-DD")

    def handle(self, *args, **options):
        source = None
        if options["source_code"]:
            try:
                source = LotterySource.objects.get(code=options["source_code"])
            except LotterySource.DoesNotExist as exc:
                raise CommandError(f"Unknown source code: {options['source_code']}") from exc

        start_date = parse_iso_date(options.get("start_date"))
        end_date = parse_iso_date(options.get("end_date"))
        if end_date < start_date:
            raise CommandError("end-date must be greater than or equal to start-date")

        summaries = sync_draw_events(source=source, start_date=start_date, end_date=end_date)
        if not summaries:
            self.stdout.write(self.style.WARNING("No active schedules found."))
            return

        for summary in summaries:
            self.stdout.write(
                f"{summary.source_code}:{summary.schedule_name} created={summary.created} updated={summary.updated}"
            )
