from rest_framework.permissions import BasePermission

from apps.workspaces.permissions import has_workspace_role


class CanManageWorkspace(BasePermission):
    def has_object_permission(self, request, view, obj):
        return has_workspace_role(request.user, obj, "admin")
