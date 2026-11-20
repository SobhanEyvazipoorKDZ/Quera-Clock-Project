from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.services import create_notification
from apps.tags.api.serializers import TagSerializer
from apps.tags.models import Tag
from apps.workspaces.models import WorkspaceMembership


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Tag.objects.visible_to(self.request.user)
        workspace = self.request.query_params.get("workspace")
        search = self.request.query_params.get("search")
        ordering = self.request.query_params.get("ordering", "name")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        if search:
            queryset = queryset.filter(name__icontains=search)
        if ordering in {"name", "-name", "created_at", "-created_at"}:
            queryset = queryset.order_by(ordering)
        return queryset

    def _notify_workspace_members(self, workspace, title, body, event_type):
        user_ids = WorkspaceMembership.objects.filter(
            workspace=workspace,
            is_active=True,
        ).values_list("user_id", flat=True)
        from apps.users.models import User

        for member in User.objects.filter(id__in=user_ids):
            create_notification(member, title=title, body=body, event_type=event_type, meta={"workspace_name": workspace.name})

    def perform_create(self, serializer):
        tag = serializer.save()
        self._notify_workspace_members(
            tag.workspace,
            title="New tag added",
            body=f"{tag.name} was added in workspace {tag.workspace.name}.",
            event_type="tag_created",
        )

    def perform_destroy(self, instance):
        workspace = instance.workspace
        tag_name = instance.name
        instance.delete()
        self._notify_workspace_members(
            workspace,
            title="Tag deleted",
            body=f"{tag_name} was deleted from workspace {workspace.name}.",
            event_type="tag_deleted",
        )
