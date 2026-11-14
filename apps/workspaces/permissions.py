from .models import WorkspaceMembership

ROLE_RANK = {
    "owner": 3,
    "admin": 2,
    "manager": 2,
    "member": 1,
}


def get_workspace_membership(user, workspace):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return (
        WorkspaceMembership.objects.enabled()
        .filter(user=user, workspace=workspace)
        .first()
    )


def get_workspace_role(user, workspace):
    if not user or not getattr(user, "is_authenticated", False):
        return None

    if workspace.owner_id == user.id:
        return WorkspaceMembership.Role.OWNER

    membership = get_workspace_membership(user, workspace)
    if membership is None:
        return None
    return membership.role


def has_workspace_role(user, workspace, minimum_role):
    role = get_workspace_role(user, workspace)
    if role is None:
        return False
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(minimum_role, 0)
