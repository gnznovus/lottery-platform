from rest_framework import serializers

from draws.models import DrawEvent
from ops.models import ScrapeRun
from results.models import DrawResult
from sources.models import LotterySource


class LotterySourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LotterySource
        fields = [
            "id",
            "code",
            "name",
            "country",
            "category",
            "timezone",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]


class DrawEventSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source.code", read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    result_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DrawEvent
        fields = [
            "id",
            "source",
            "source_code",
            "source_name",
            "scheduled_date",
            "resolved_date",
            "period_code",
            "status",
            "resolution_method",
            "resolution_source_url",
            "resolved_at",
            "result_published_at",
            "scraped_at",
            "completed_at",
            "notes",
            "result_count",
            "created_at",
            "updated_at",
        ]


class DrawResultSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="draw_event.source.code", read_only=True)
    draw_date = serializers.DateField(source="draw_event.resolved_date", read_only=True)
    scheduled_date = serializers.DateField(source="draw_event.scheduled_date", read_only=True)
    reward_type_code = serializers.CharField(source="reward_type.code", read_only=True)
    reward_type_name = serializers.CharField(source="reward_type.name", read_only=True)

    class Meta:
        model = DrawResult
        fields = [
            "id",
            "draw_event",
            "source_code",
            "draw_date",
            "scheduled_date",
            "reward_type",
            "reward_type_code",
            "reward_type_name",
            "value",
            "sequence",
            "raw_label",
            "metadata",
            "created_at",
            "updated_at",
        ]


class ScrapeRunSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source.code", read_only=True)
    draw_event_date = serializers.DateField(source="draw_event.scheduled_date", read_only=True)

    class Meta:
        model = ScrapeRun
        fields = [
            "id",
            "source",
            "source_code",
            "draw_event",
            "draw_event_date",
            "job_type",
            "status",
            "started_at",
            "finished_at",
            "message",
            "error_details",
            "raw_snapshot_path",
            "metadata",
        ]


class SourceLatestResultsSerializer(serializers.Serializer):
    source = LotterySourceSerializer()
    draw_event = DrawEventSerializer()
    results = DrawResultSerializer(many=True)


class SourceLatestSummarySerializer(serializers.Serializer):
    source_code = serializers.CharField(source="source.code")
    source_name = serializers.CharField(source="source.name")
    category = serializers.CharField(source="source.category")
    draw_event = DrawEventSerializer()
    results = DrawResultSerializer(many=True)
