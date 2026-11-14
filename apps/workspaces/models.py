from django.conf import settings
from django.db import models

from core.models import TimestampedModel
from core.models.base import SoftDeleteManager, SoftDeleteQuerySet


class WorkspaceQuerySet(SoftDeleteQuerySet):
    def visible_to(self, user):
        if not user or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(
            memberships__user=user,
            memberships__is_active=True,
            memberships__is_deleted=False,
        ).distinct()


class Workspace(TimestampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="workspaces/", blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_workspaces",
    )

    objects = SoftDeleteManager.from_queryset(WorkspaceQuerySet)()

    class Meta:
        ordering = ("name", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "name"),
                condition=models.Q(is_deleted=False),
                name="unique_workspace_name_per_owner",
            )
        ]

    def __str__(self):
        return self.name


class WorkspaceMembershipQuerySet(SoftDeleteQuerySet):
    def enabled(self):
        return self.filter(is_active=True, is_deleted=False)

    def for_user(self, user):
        return self.enabled().filter(user=user)


class WorkspaceMembership(TimestampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager.from_queryset(WorkspaceMembershipQuerySet)()

    class Meta:
        ordering = ("workspace__name", "user__mobile")
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "user"),
                condition=models.Q(is_deleted=False),
                name="unique_workspace_membership",
            )
        ]

    def __str__(self):
        return f"{self.user} @ {self.workspace}"
