from collections import defaultdict

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.time_entries.api.serializers import TimeEntrySerializer
from apps.time_entries.models import TimeEntry


class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TimeEntry.objects.visible_to(self.request.user).select_related(
            "workspace",
            "project",
            "user",
        ).prefetch_related("tags")

    @action(detail=False, methods=["post"])
    def start(self, request):
        serializer = self.get_serializer(data={**request.data, "start_time": request.data.get("start_time") or timezone.now()})
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        return Response(self.get_serializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def running(self, request):
        entry = self.get_queryset().running().first()
        if not entry:
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        entry = self.get_object()
        end_time = request.data.get("end_time")
        parsed_end = parse_datetime(end_time) if end_time else timezone.now()
        if parsed_end <= entry.start_time:
            raise ValidationError({"end_time": "End time must be greater than start time."})
        entry.stop(parsed_end)
        return Response(self.get_serializer(entry).data)

    def list(self, request, *args, **kwargs):
        return self.grouped(request)

    @action(detail=False, methods=["get"])
    def grouped(self, request):
        groups = defaultdict(lambda: {"total_ms": 0, "entries": []})
        for entry in self.get_queryset().order_by("-start_time", "-created_at"):
            key = entry.start_time.date().isoformat()
            data = self.get_serializer(entry).data
            groups[key]["entries"].append(data)
            groups[key]["total_ms"] += (entry.duration_seconds or 0) * 1000

        return Response({
            "items_per_page": 10,
            "current_page_items_count": sum(len(value["entries"]) for value in groups.values()),
            "total_items": sum(len(value["entries"]) for value in groups.values()),
            "offset": 0,
            "next_offset": None,
            "has_more": False,
            "server_now_ms": int(timezone.now().timestamp() * 1000),
            "server_now": timezone.now().isoformat(),
            "groups": [
                {
                    "key": key,
                    "week_start": key,
                    "week_end": key,
                    "total_ms": value["total_ms"],
                    "days": [{
                        "key": key,
                        "date": key,
                        "total_ms": value["total_ms"],
                        "entries": value["entries"],
                    }],
                }
                for key, value in groups.items()
            ],
        })
