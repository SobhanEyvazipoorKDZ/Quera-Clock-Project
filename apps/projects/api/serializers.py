from rest_framework import serializers

from apps.clients.models import Client
from apps.projects.models import Project
from apps.workspaces.models import Workspace


class AbsoluteImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None
        url = value.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ProjectSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    client_id = serializers.PrimaryKeyRelatedField(
        source="client",
        queryset=Client.objects.all(),
        allow_null=True,
        required=False,
        write_only=True,
    )
    thumbnail = AbsoluteImageField(required=False, allow_null=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "workspace",
            "name",
            "color",
            "description",
            "thumbnail",
            "is_archived",
            "client",
            "client_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        validators = []

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        if data.get("clear_thumbnail") in ("true", "True", True):
            data["thumbnail"] = None
        data.pop("clear_thumbnail", None)
        if "workspace_id" in data and "workspace" not in data:
            data["workspace"] = data.get("workspace_id")
        if "client" in data and "client_id" not in data:
            raw_client = data.get("client")
            if raw_client in ("", None):
                data["client_id"] = None
            elif isinstance(raw_client, dict):
                data["client_id"] = raw_client.get("id")
            else:
                data["client_id"] = raw_client
        if "client_id" in data and data.get("client_id") == "":
            data["client_id"] = None
        return super().to_internal_value(data)

    def get_client(self, obj):
        if not obj.client_id:
            return None
        request = self.context.get("request")
        thumbnail = obj.client.thumbnail.url if obj.client.thumbnail else None
        if request and thumbnail:
            thumbnail = request.build_absolute_uri(thumbnail)
        return {
            "id": str(obj.client_id),
            "name": obj.client.name,
            "thumbnail": thumbnail,
        }

    def validate(self, attrs):
        workspace = attrs.get("workspace") or (self.instance.workspace if self.instance else None)
        name = attrs.get("name") if "name" in attrs else (self.instance.name if self.instance else None)
        client = attrs.get("client") if "client" in attrs else (self.instance.client if self.instance else None)
        request = self.context.get("request")

        if workspace and request and not Workspace.objects.visible_to(request.user).filter(pk=workspace.pk).exists():
            raise serializers.ValidationError({"workspace": "You do not have access to this workspace."})

        if workspace and name:
            queryset = Project.objects.filter(workspace=workspace, name__iexact=name.strip())
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({
                    "name": "A project with this name already exists in this workspace."
                })
            attrs["name"] = name.strip()

        if workspace and client and client.workspace_id != workspace.id:
            raise serializers.ValidationError({
                "client_id": "Selected client does not belong to this workspace."
            })

        return attrs
