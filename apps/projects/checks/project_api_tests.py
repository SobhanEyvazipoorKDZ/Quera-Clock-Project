from django.test import override_settings
from rest_framework.test import APITestCase

from apps.clients.models import Client
from apps.notifications.models import Notification
from apps.projects.models import Project
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ProjectApiChecks(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(mobile="09123330001", password="pass12345")
        self.member = User.objects.create_user(mobile="09123330002", password="pass12345")
        self.outsider = User.objects.create_user(mobile="09123330003", password="pass12345")
        self.workspace = Workspace.objects.create(name="Team", owner=self.owner)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.member)
        self.hidden_workspace = Workspace.objects.create(name="Hidden", owner=self.outsider)
        self.client_obj = Client.objects.create(workspace=self.workspace, name="Acme")
        self.project = Project.objects.create(workspace=self.workspace, client=self.client_obj, name="Website")

    def test_owner_can_create_project(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/projects/",
            {"workspace": self.workspace.id, "client_id": self.client_obj.id, "name": "Mobile"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_member_only_sees_visible_projects(self):
        Project.objects.create(workspace=self.hidden_workspace, name="Hidden Project")
        self.client.force_authenticate(user=self.member)
        response = self.client.get("/api/projects/")
        self.assertEqual(response.status_code, 200)
        names = {item["name"] for item in response.json()["results"]}
        self.assertEqual(names, {"Website"})

    def test_client_must_belong_to_project_workspace(self):
        hidden_client = Client.objects.create(workspace=self.hidden_workspace, name="Hidden Client")
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/projects/",
            {"workspace": self.workspace.id, "client_id": hidden_client.id, "name": "Wrong Client"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_archive_action_archives_project(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f"/api/projects/{self.project.id}/archive/")
        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_archived)

    def test_project_creation_creates_notification(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            "/api/projects/",
            {"workspace": self.workspace.id, "name": "Notified"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Notification.objects.filter(event_type="project_created").exists())
