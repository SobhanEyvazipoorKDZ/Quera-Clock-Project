from rest_framework import serializers

from apps.clients.models import Client
from apps.workspaces.models import Workspace


class AbsoluteImageField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None
        url = value.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ClientSerializer(serializers.ModelSerializer):
    thumbnail = AbsoluteImageField(required=False, allow_null=True)

    class Meta:
        model = Client
        fields = "__all__"
        validators = []

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        if data.get("clear_thumbnail") in ("true", "True", True):
            data["thumbnail"] = None
        data.pop("clear_thumbnail", None)
        if "workspace_id" in data and "workspace" not in data:
            data["workspace"] = data.get("workspace_id")
        if "client_id" in data and "client" not in data:
            data["client"] = data.get("client_id")
        return super().to_internal_value(data)

    def validate(self, attrs):
        workspace = attrs.get("workspace") or (self.instance.workspace if self.instance else None)
        name = attrs.get("name") if "name" in attrs else (self.instance.name if self.instance else None)
        request = self.context.get("request")
        if workspace and request and not Workspace.objects.visible_to(request.user).filter(pk=workspace.pk).exists():
            raise serializers.ValidationError({"workspace": "You do not have access to this workspace."})
        if workspace and name:
            queryset = Client.objects.filter(workspace=workspace, name__iexact=name.strip())
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({
                    "name": "A client with this name already exists in this workspace."
                })
            attrs["name"] = name.strip()
        return attrs
