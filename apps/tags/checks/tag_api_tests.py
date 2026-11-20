from django.test import override_settings
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.tags.models import Tag
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TagApiChecks(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(mobile="09122220001", password="pass12345")
        self.member = User.objects.create_user(mobile="09122220002", password="pass12345")
        self.outsider = User.objects.create_user(mobile="09122220003", password="pass12345")
        self.workspace = Workspace.objects.create(name="Team", owner=self.owner)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.member)
        self.hidden_workspace = Workspace.objects.create(name="Hidden", owner=self.outsider)
        self.tag = Tag.objects.create(workspace=self.workspace, name="Backend")

    def test_owner_can_create_tag(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/tags/",
            {"workspace": self.workspace.id, "name": "Design", "color": "#f97316"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_member_only_sees_visible_tags(self):
        Tag.objects.create(workspace=self.hidden_workspace, name="Hidden")
        self.client.force_authenticate(user=self.member)
        response = self.client.get("/api/tags/")
        self.assertEqual(response.status_code, 200)
        names = {item["name"] for item in response.json()["results"]}
        self.assertEqual(names, {"Backend"})

    def test_duplicate_name_is_rejected_in_workspace(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/tags/",
            {"workspace": self.workspace.id, "name": "Backend"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_member_cannot_create_tag_in_hidden_workspace(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            "/api/tags/",
            {"workspace": self.hidden_workspace.id, "name": "Illegal"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_tag_creation_creates_notification(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/tags/",
            {"workspace": self.workspace.id, "name": "Notified"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Notification.objects.filter(event_type="tag_created").exists())
