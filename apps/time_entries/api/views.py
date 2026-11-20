from collections import defaultdict

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.time_entries.api.serializers import TimeEntrySerializer
from apps.time_entries.models import TimeEntry
from core.cache import (
    bump_user_cache_version,
    get_cached_response,
    request_cache_key,
    set_cached_response,
)


class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer
    permission_classes = [IsAuthenticated]
    cache_namespace = "timesheet"

    def get_queryset(self):
        queryset = TimeEntry.objects.visible_to(self.request.user).select_related(
            "workspace",
            "project",
            "project__client",
            "user",
        ).prefetch_related("tags")
        workspace = self.request.query_params.get("workspace")
        project = self.request.query_params.get("project") or self.request.query_params.get("project_id")
        client = self.request.query_params.get("client") or self.request.query_params.get("client_id")
        search = self.request.query_params.get("search")
        status_filter = self.request.query_params.get("status")
        started_after = self.request.query_params.get("started_after")
        started_before = self.request.query_params.get("started_before")
        tag_ids = []
        for key in ("tags", "tag", "tag_id"):
            for raw_value in self.request.query_params.getlist(key):
                tag_ids.extend(value.strip() for value in str(raw_value).split(",") if value.strip())
        ordering = self.request.query_params.get("ordering", "-start_time")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        if project:
            queryset = queryset.filter(project_id=project)
        if client:
            queryset = queryset.filter(project__client_id=client)
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search)
                | Q(project__name__icontains=search)
                | Q(tags__name__icontains=search)
            )
        if status_filter == "running":
            queryset = queryset.filter(end_time__isnull=True)
        elif status_filter == "ended":
            queryset = queryset.filter(end_time__isnull=False)
        if started_after:
            dt = parse_datetime(started_after)
            if dt:
                queryset = queryset.filter(start_time__gte=dt)
        if started_before:
            dt = parse_datetime(started_before)
            if dt:
                queryset = queryset.filter(start_time__lte=dt)
        if tag_ids:
            queryset = queryset.filter(tags__id__in=tag_ids)
        if ordering in {"start_time", "-start_time", "created_at", "-created_at"}:
            queryset = queryset.order_by(ordering)
        return queryset.distinct()

    def perform_create(self, serializer):
        entry = serializer.save()
        bump_user_cache_version(entry.user_id, self.cache_namespace)

    def perform_update(self, serializer):
        entry = serializer.save()
        bump_user_cache_version(entry.user_id, self.cache_namespace)

    def perform_destroy(self, instance):
        user_id = instance.user_id
        instance.delete()
        bump_user_cache_version(user_id, self.cache_namespace)

    @action(detail=False, methods=["post"])
    def start(self, request):
        serializer = self.get_serializer(data={**request.data, "start_time": request.data.get("start_time") or timezone.now()})
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        bump_user_cache_version(entry.user_id, self.cache_namespace)
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
        bump_user_cache_version(entry.user_id, self.cache_namespace)
        return Response(self.get_serializer(entry).data)

    def list(self, request, *args, **kwargs):
        return self.grouped(request)

    @action(detail=False, methods=["get"])
    def grouped(self, request):
        cache_key = request_cache_key(request.user.id, self.cache_namespace, request.query_params)
        cached_payload = get_cached_response(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        groups = defaultdict(lambda: {"total_ms": 0, "entries": []})
        for entry in self.get_queryset():
            key = entry.start_time.date().isoformat()
            data = self.get_serializer(entry).data
            groups[key]["entries"].append(data)
            groups[key]["total_ms"] += (entry.duration_seconds or 0) * 1000

        payload = {
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
        }
        return Response(set_cached_response(cache_key, payload))
