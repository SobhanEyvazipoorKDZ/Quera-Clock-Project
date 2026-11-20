from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.services import create_notification
from apps.projects.api.serializers import ProjectSerializer
from apps.projects.models import Project
from apps.workspaces.models import WorkspaceMembership


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Project.objects.visible_to(self.request.user).select_related("client")
        workspace = self.request.query_params.get("workspace")
        search = self.request.query_params.get("search")
        client = self.request.query_params.get("client")
        clients = self.request.query_params.getlist("clients")
        is_archived = self.request.query_params.get("is_archived")
        ordering = self.request.query_params.get("ordering", "-created_at")
        if workspace:
            queryset = queryset.filter(workspace_id=workspace)
        if search:
            queryset = queryset.filter(name__icontains=search)
        if client:
            queryset = queryset.filter(client_id=client)
        if clients:
            queryset = queryset.filter(client_id__in=clients)
        if is_archived in {"true", "false"}:
            queryset = queryset.filter(is_archived=(is_archived == "true"))
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
        project = serializer.save()
        self._notify_workspace_members(
            project.workspace,
            title="New project added",
            body=f"{project.name} was added in workspace {project.workspace.name}.",
            event_type="project_created",
        )

    def perform_destroy(self, instance):
        workspace = instance.workspace
        project_name = instance.name
        instance.delete()
        self._notify_workspace_members(
            workspace,
            title="Project deleted",
            body=f"{project_name} was deleted from workspace {workspace.name}.",
            event_type="project_deleted",
        )

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        project = self.get_object()
        project.is_archived = True
        project.save(update_fields=["is_archived", "updated_at"])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        project = self.get_object()
        project.is_archived = False
        project.save(update_fields=["is_archived", "updated_at"])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        return self.unarchive(request, pk=pk)
