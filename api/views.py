from datetime import date

from django.db.models import Count
from django.db.models.functions import Coalesce
from django.http import Http404
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from draws.models import DrawEvent
from ops.models import ScrapeRun
from results.models import DrawResult
from sources.models import LotterySource

from .permissions import ApiKeyPermission
from .serializers import (
    DrawEventSerializer,
    DrawResultSerializer,
    LotterySourceSerializer,
    ScrapeRunSerializer,
    SourceLatestResultsSerializer,
    SourceLatestSummarySerializer,
)


class PublicReadOnlyViewMixin:
    permission_classes = [ApiKeyPermission]
    authentication_classes = []


class SourceLatestPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class SourceListView(PublicReadOnlyViewMixin, generics.ListAPIView):
    serializer_class = LotterySourceSerializer
    queryset = LotterySource.objects.all().order_by("code")

    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        return queryset


class SourceDetailView(PublicReadOnlyViewMixin, generics.RetrieveAPIView):
    serializer_class = LotterySourceSerializer
    queryset = LotterySource.objects.all()
    lookup_field = "code"
    lookup_url_kwarg = "source_code"


class DrawEventListView(PublicReadOnlyViewMixin, generics.ListAPIView):
    serializer_class = DrawEventSerializer

    def get_queryset(self):
        queryset = (
            DrawEvent.objects.select_related("source")
            .annotate(result_count=Count("results"))
            .order_by("-scheduled_date", "source__code", "-id")
        )
        source_code = self.request.query_params.get("source")
        status = self.request.query_params.get("status")
        scheduled_date = self.request.query_params.get("scheduled_date")

        if source_code:
            queryset = queryset.filter(source__code=source_code)
        if status:
            queryset = queryset.filter(status=status)
        if scheduled_date:
            queryset = queryset.filter(scheduled_date=scheduled_date)
        return queryset


class DrawEventDetailView(PublicReadOnlyViewMixin, generics.RetrieveAPIView):
    serializer_class = DrawEventSerializer

    def get_queryset(self):
        return DrawEvent.objects.select_related("source").annotate(result_count=Count("results"))


class DrawEventResultsView(PublicReadOnlyViewMixin, generics.ListAPIView):
    serializer_class = DrawResultSerializer

    def get_queryset(self):
        return DrawResult.objects.select_related("draw_event__source", "reward_type").filter(
            draw_event_id=self.kwargs["pk"]
        ).order_by("reward_type__sort_order", "sequence", "id")


class DrawResultListView(PublicReadOnlyViewMixin, generics.ListAPIView):
    serializer_class = DrawResultSerializer

    def get_queryset(self):
        queryset = DrawResult.objects.select_related("draw_event__source", "reward_type").order_by(
            "-draw_event__scheduled_date", "draw_event__source__code", "reward_type__sort_order", "sequence", "id"
        )
        source_code = self.request.query_params.get("source")
        draw_date = self.request.query_params.get("draw_date")
        reward_type = self.request.query_params.get("reward_type")

        if source_code:
            queryset = queryset.filter(draw_event__source__code=source_code)
        if draw_date:
            queryset = queryset.filter(draw_event__scheduled_date=draw_date)
        if reward_type:
            queryset = queryset.filter(reward_type__code=reward_type)
        return queryset


class ScrapeRunListView(PublicReadOnlyViewMixin, generics.ListAPIView):
    serializer_class = ScrapeRunSerializer
    queryset = ScrapeRun.objects.select_related("source", "draw_event").order_by("-started_at", "-id")

    def get_queryset(self):
        queryset = super().get_queryset()
        source_code = self.request.query_params.get("source")
        status = self.request.query_params.get("status")
        job_type = self.request.query_params.get("job_type")

        if source_code:
            queryset = queryset.filter(source__code=source_code)
        if status:
            queryset = queryset.filter(status=status)
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        return queryset


class ScrapeRunDetailView(PublicReadOnlyViewMixin, generics.RetrieveAPIView):
    serializer_class = ScrapeRunSerializer
    queryset = ScrapeRun.objects.select_related("source", "draw_event")


class SourceLatestResultsView(PublicReadOnlyViewMixin, APIView):
    def get(self, _request, source_code: str):
        try:
            source = LotterySource.objects.get(code=source_code)
        except LotterySource.DoesNotExist as exc:
            raise Http404("Source not found") from exc

        draw_event = (
            DrawEvent.objects.select_related("source")
            .annotate(latest_date=Coalesce("resolved_date", "scheduled_date"))
            .filter(source=source, status=DrawEvent.Status.COMPLETED)
            .order_by("-latest_date", "-id")
            .first()
        )
        if draw_event is None:
            raise Http404("No completed draw event found for source")

        draw_event = (
            DrawEvent.objects.select_related("source")
            .annotate(result_count=Count("results"))
            .get(pk=draw_event.pk)
        )
        results = list(
            DrawResult.objects.select_related("draw_event__source", "reward_type").filter(draw_event=draw_event)
            .order_by("reward_type__sort_order", "sequence", "id")
        )

        payload = {
            "source": source,
            "draw_event": draw_event,
            "results": results,
        }
        serializer = SourceLatestResultsSerializer(payload)
        return Response(serializer.data)


class SourcesLatestResultsView(PublicReadOnlyViewMixin, APIView):
    pagination_class = SourceLatestPagination

    def get(self, request):
        source_codes = request.query_params.get("sources")
        queryset = LotterySource.objects.filter(is_active=True).order_by("code")
        if source_codes:
            requested_codes = [code.strip() for code in source_codes.split(",") if code.strip()]
            queryset = queryset.filter(code__in=requested_codes)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        items = []
        for source in page:
            draw_event = (
                DrawEvent.objects.select_related("source")
                .annotate(latest_date=Coalesce("resolved_date", "scheduled_date"), result_count=Count("results"))
                .filter(source=source, status=DrawEvent.Status.COMPLETED)
                .order_by("-latest_date", "-id")
                .first()
            )
            if draw_event is None:
                continue

            results = list(
                DrawResult.objects.select_related("draw_event__source", "reward_type").filter(draw_event=draw_event)
                .order_by("reward_type__sort_order", "sequence", "id")
            )
            items.append(
                {
                    "source": source,
                    "draw_event": draw_event,
                    "results": results,
                }
            )

        serializer = SourceLatestSummarySerializer(items, many=True)
        return paginator.get_paginated_response(serializer.data)


class SearchResultsView(PublicReadOnlyViewMixin, APIView):
    def get(self, request):
        source_code = (request.query_params.get("source") or "").strip()
        draw_date = (request.query_params.get("draw_date") or "").strip()
        number = (request.query_params.get("number") or "").strip()

        if not source_code or not draw_date or not number:
            return Response(
                {"detail": "source, draw_date, and number are required."},
                status=400,
            )

        if not number.isdigit() or len(number) != 6:
            return Response(
                {"detail": "number must be a 6-digit string."},
                status=400,
            )

        try:
            parsed_date = date.fromisoformat(draw_date)
        except ValueError:
            return Response(
                {"detail": "draw_date must be YYYY-MM-DD."},
                status=400,
            )

        try:
            source = LotterySource.objects.get(code=source_code)
        except LotterySource.DoesNotExist as exc:
            raise Http404("Source not found") from exc

        draw_event = (
            DrawEvent.objects.select_related("source")
            .annotate(match_date=Coalesce("resolved_date", "scheduled_date"))
            .filter(source=source, status=DrawEvent.Status.COMPLETED, match_date=parsed_date)
            .order_by("-id")
            .first()
        )
        if draw_event is None:
            raise Http404("No completed draw event found for date")

        front_three = number[:3]
        back_three = number[-3:]
        last_two = number[-2:]

        full_match_codes = {
            "first_prize",
            "near_first_prize",
            "prize_2",
            "prize_3",
            "prize_4",
            "prize_5",
            "full_result",
        }
        front_three_codes = {"front_3_digits", "top_3_digits"}
        back_three_codes = {"back_3_digits"}
        last_two_codes = {"last_2_digits", "bottom_2_digits"}
        known_codes = full_match_codes | front_three_codes | back_three_codes | last_two_codes

        results_qs = (
            DrawResult.objects.select_related("draw_event__source", "reward_type")
            .filter(draw_event=draw_event)
            .order_by("reward_type__sort_order", "sequence", "id")
        )

        matches = []
        for result in results_qs:
            value = (result.value or "").strip()
            if not value:
                continue
            code = result.reward_type.code

            if code in front_three_codes and value == front_three:
                matches.append(result)
                continue
            if code in back_three_codes and value == back_three:
                matches.append(result)
                continue
            if code in last_two_codes and value == last_two:
                matches.append(result)
                continue
            if code in full_match_codes and value == number:
                matches.append(result)
                continue

            # Fallback for unknown reward types based on value length.
            if code not in known_codes:
                if len(value) == 6 and value == number:
                    matches.append(result)
                elif len(value) == 3 and value == back_three:
                    matches.append(result)
                elif len(value) == 2 and value == last_two:
                    matches.append(result)

        serializer = DrawResultSerializer(matches, many=True)
        return Response(
            {
                "source_code": source.code,
                "source_name": source.name,
                "draw_event_id": draw_event.id,
                "draw_date": str(draw_event.resolved_date or draw_event.scheduled_date),
                "number": number,
                "matches": serializer.data,
            }
        )

