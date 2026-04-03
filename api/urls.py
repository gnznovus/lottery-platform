from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import ApiKeyPermission
from .views import (
    DrawEventDetailView,
    DrawEventListView,
    DrawEventResultsView,
    DrawResultListView,
    ScrapeRunDetailView,
    ScrapeRunListView,
    SearchResultsView,
    SourceDetailView,
    SourceLatestResultsView,
    SourceListView,
    SourcesLatestResultsView,
)


class ApiRootView(APIView):
    permission_classes = [ApiKeyPermission]
    authentication_classes = []

    def get(self, _request):
        return Response(
            {
                "name": "lottery-platform",
                "status": "ready",
                "endpoints": {
                    "sources": "/api/sources/",
                    "source_detail": "/api/sources/<source_code>/",
                    "source_latest_results": "/api/sources/<source_code>/results/latest/",
                    "sources_latest_results": "/api/sources/results/latest/",
                    "draw_events": "/api/draw-events/",
                    "draw_event_detail": "/api/draw-events/<id>/",
                    "draw_event_results": "/api/draw-events/<id>/results/",
                    "results": "/api/results/",
                    "scrape_runs": "/api/scrape-runs/",
                    "scrape_run_detail": "/api/scrape-runs/<id>/",
                    "search": "/api/search/?source=<code>&draw_date=YYYY-MM-DD&number=123456",
                },
            }
        )


urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("sources/", SourceListView.as_view(), name="source-list"),
    path("sources/results/latest/", SourcesLatestResultsView.as_view(), name="sources-latest-results"),
    path("sources/<slug:source_code>/", SourceDetailView.as_view(), name="source-detail"),
    path("sources/<slug:source_code>/results/latest/", SourceLatestResultsView.as_view(), name="source-latest-results"),
    path("draw-events/", DrawEventListView.as_view(), name="draw-event-list"),
    path("draw-events/<int:pk>/", DrawEventDetailView.as_view(), name="draw-event-detail"),
    path("draw-events/<int:pk>/results/", DrawEventResultsView.as_view(), name="draw-event-results"),
    path("results/", DrawResultListView.as_view(), name="draw-result-list"),
    path("scrape-runs/", ScrapeRunListView.as_view(), name="scrape-run-list"),
    path("scrape-runs/<int:pk>/", ScrapeRunDetailView.as_view(), name="scrape-run-detail"),
    path("search/", SearchResultsView.as_view(), name="search-results"),
]
