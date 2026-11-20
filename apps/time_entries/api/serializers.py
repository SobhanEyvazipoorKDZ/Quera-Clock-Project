from django.utils import timezone
from rest_framework import serializers

from apps.time_entries.models import TimeEntry
from apps.workspaces.models import Workspace


class TimeEntrySerializer(serializers.ModelSerializer):
    duration_seconds = serializers.IntegerField(read_only=True)
    start_time_ms = serializers.SerializerMethodField()
    end_time_ms = serializers.SerializerMethodField()
    server_now_ms = serializers.SerializerMethodField()
    project_details = serializers.SerializerMethodField()
    tag_details = serializers.SerializerMethodField()

    class Meta:
        model = TimeEntry
        fields = (
            "id", "workspace", "user", "project", "project_details", "tags", "tag_details",
            "description", "start_time", "start_time_ms", "end_time", "end_time_ms", "server_now_ms",
            "duration", "duration_seconds", "is_billable", "created_at", "updated_at",
        )
        read_only_fields = ("id", "user", "duration", "duration_seconds", "created_at", "updated_at")

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        if "workspace_id" in data and "workspace" not in data:
            data["workspace"] = data.get("workspace_id")
        if "project_id" in data and "project" not in data:
            data["project"] = data.get("project_id")
        return super().to_internal_value(data)

    def get_start_time_ms(self, obj):
        return int(obj.start_time.timestamp() * 1000)

    def get_end_time_ms(self, obj):
        return int(obj.end_time.timestamp() * 1000) if obj.end_time else None

    def get_server_now_ms(self, obj):
        return int(timezone.now().timestamp() * 1000)

    def get_project_details(self, obj):
        if not obj.project:
            return None
        return {
            "id": str(obj.project_id),
            "name": obj.project.name,
            "is_deleted": False,
            "client_name": obj.project.client.name if obj.project.client else None,
        }

    def get_tag_details(self, obj):
        return [
            {"id": str(tag.id), "name": tag.name, "color": tag.color, "is_deleted": False}
            for tag in obj.tags.all()
        ]

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        entry = TimeEntry.objects.create(user=self.context["request"].user, **validated_data)
        entry.tags.set(tags)
        return entry

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        workspace = attrs.get("workspace") or (instance.workspace if instance else None)
        project = attrs.get("project") if "project" in attrs else (instance.project if instance else None)
        start_time = attrs.get("start_time") or (instance.start_time if instance else None)
        end_time = attrs.get("end_time") if "end_time" in attrs else (instance.end_time if instance else None)
        tags = attrs.get("tags")
        request = self.context.get("request")

        if workspace and request and not Workspace.objects.visible_to(request.user).filter(pk=workspace.pk).exists():
            raise serializers.ValidationError({"workspace": "You do not have access to this workspace."})

        if workspace and request and end_time is None:
            running = TimeEntry.objects.filter(
                workspace=workspace,
                user=request.user,
                end_time__isnull=True,
            )
            if instance:
                running = running.exclude(pk=instance.pk)
            if running.exists():
                raise serializers.ValidationError({
                    "end_time": "You already have a running time entry in this workspace."
                })

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({
                "end_time": "End time must be greater than start time."
            })

        if workspace and project and project.workspace_id != workspace.id:
            raise serializers.ValidationError({
                "project": "Selected project does not belong to this workspace."
            })

        if workspace and tags:
            invalid_tag = next((tag for tag in tags if tag.workspace_id != workspace.id), None)
            if invalid_tag:
                raise serializers.ValidationError({
                    "tags": "All selected tags must belong to the same workspace."
                })

        return attrs
