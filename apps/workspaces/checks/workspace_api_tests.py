from django.test import override_settings
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WorkspaceApiChecks(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(mobile="09128880001", password="pass12345")
        self.member = User.objects.create_user(mobile="09128880002", password="pass12345")
        self.new_user = User.objects.create_user(mobile="09128880003", password="pass12345")
        self.workspace = Workspace.objects.create(name="Team", owner=self.owner)
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=WorkspaceMembership.Role.MEMBER,
        )

    def test_owner_can_create_workspace(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post("/api/workspaces/", {"name": "Product"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Workspace.objects.filter(name="Product", owner=self.owner).exists())

    def test_member_only_sees_joined_workspaces(self):
        Workspace.objects.create(name="Hidden", owner=self.new_user)
        self.client.force_authenticate(user=self.member)
        response = self.client.get("/api/workspaces/")
        self.assertEqual(response.status_code, 200)
        names = {item["name"] for item in response.json()["results"]}
        self.assertEqual(names, {"Team"})

    def test_owner_can_add_member(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/workspace-memberships/",
            {
                "workspace": self.workspace.id,
                "user_id": self.new_user.id,
                "role": WorkspaceMembership.Role.MEMBER,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_member_cannot_add_member(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            "/api/workspace-memberships/",
            {
                "workspace": self.workspace.id,
                "user_id": self.new_user.id,
                "role": WorkspaceMembership.Role.MEMBER,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_adding_member_creates_notification(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/workspace-memberships/",
            {
                "workspace": self.workspace.id,
                "user_id": self.new_user.id,
                "role": WorkspaceMembership.Role.MEMBER,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            Notification.objects.filter(
                user=self.new_user,
                event_type="workspace_membership_added",
            ).exists()
        )
