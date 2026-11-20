from rest_framework import serializers

from apps.tags.models import Tag
from apps.workspaces.models import Workspace


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"
        validators = []

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        if "workspace_id" in data and "workspace" not in data:
            data["workspace"] = data.get("workspace_id")
        return super().to_internal_value(data)

    def validate(self, attrs):
        workspace = attrs.get("workspace") or (self.instance.workspace if self.instance else None)
        name = attrs.get("name") if "name" in attrs else (self.instance.name if self.instance else None)
        request = self.context.get("request")
        if workspace and request and not Workspace.objects.visible_to(request.user).filter(pk=workspace.pk).exists():
            raise serializers.ValidationError({"workspace": "You do not have access to this workspace."})
        if workspace and name:
            queryset = Tag.objects.filter(workspace=workspace, name__iexact=name.strip())
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({
                    "name": "A tag with this name already exists in this workspace."
                })
            attrs["name"] = name.strip()
        return attrs
