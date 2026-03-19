from django.db import transaction
from django.utils import timezone

from draws.models import DrawEvent
from results.models import DrawResult, RewardType
from scraping.date_utils import parse_draw_date_value
from scraping.types import ScrapePayload
from sources.models import LotterySource


def _reward_definition_map(config: dict) -> dict[str, dict]:
    return {definition['reward_type']: definition for definition in config.get('reward_definitions', [])}


def _display_name_for_reward(definition: dict) -> str:
    return definition.get('label') or definition.get('display_name') or definition['reward_type'].replace('_', ' ').title()


def ensure_reward_types(source: LotterySource, config: dict) -> dict[str, RewardType]:
    reward_types = {}
    for index, definition in enumerate(config.get('reward_definitions', []), start=1):
        reward_type, _ = RewardType.objects.update_or_create(
            source=source,
            code=definition['reward_type'],
            defaults={
                'name': _display_name_for_reward(definition),
                'digit_length': definition.get('digit_length'),
                'expected_count': definition.get('expected_count'),
                'is_required': definition.get('required', True),
                'sort_order': index,
            },
        )
        reward_types[definition['reward_type']] = reward_type
    return reward_types


@transaction.atomic
def persist_scrape_payload(
    source: LotterySource,
    payload: ScrapePayload,
    config: dict,
    *,
    requested_draw_date: str | None = None,
) -> DrawEvent:
    resolved_draw_date = parse_draw_date_value(payload.draw_date)
    if resolved_draw_date is None:
        raise ValueError('Payload draw_date is required for persistence')

    scheduled_draw_date = parse_draw_date_value(requested_draw_date) or resolved_draw_date
    dates_shifted = scheduled_draw_date != resolved_draw_date

    draw_event, _ = DrawEvent.objects.update_or_create(
        source=source,
        scheduled_date=scheduled_draw_date,
        period_code='',
        defaults={
            'resolved_date': resolved_draw_date,
            'status': DrawEvent.Status.SCRAPED,
            'resolution_method': DrawEvent.ResolutionMethod.SYSTEM_INFERENCE,
            'resolution_source_url': payload.fetched_url,
            'resolved_at': timezone.now(),
            'scraped_at': timezone.now(),
            'notes': (
                f'Scraped from {payload.fetched_url}. '
                f'Requested {scheduled_draw_date.isoformat()}, resolved {resolved_draw_date.isoformat()}.'
                if dates_shifted
                else f'Scraped from {payload.fetched_url}.'
            ),
        },
    )

    reward_types = ensure_reward_types(source, config)
    DrawResult.objects.filter(draw_event=draw_event).delete()

    for field in payload.extracted_fields:
        reward_type = reward_types[field.reward_type]
        for sequence, value in enumerate(field.values, start=1):
            DrawResult.objects.create(
                draw_event=draw_event,
                reward_type=reward_type,
                value=value,
                sequence=sequence,
                raw_label=field.raw_label,
                metadata=field.metadata,
            )

    draw_event.resolved_date = resolved_draw_date
    draw_event.status = DrawEvent.Status.COMPLETED
    draw_event.completed_at = timezone.now()
    draw_event.save(update_fields=['resolved_date', 'status', 'completed_at'])
    return draw_event
