from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.projects.models import Project
from apps.tags.models import Tag
from apps.time_entries.models import TimeEntry
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMembership


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TimeTrackingApiChecks(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(mobile="09124440001", password="pass12345")
        self.member = User.objects.create_user(mobile="09124440002", password="pass12345")
        self.workspace = Workspace.objects.create(name="Team", owner=self.owner)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.member)
        self.project = Project.objects.create(workspace=self.workspace, name="Website")
        self.tag = Tag.objects.create(workspace=self.workspace, name="Backend")
        self.start = timezone.now() - timedelta(hours=2)
        self.end = timezone.now() - timedelta(hours=1)

    def test_start_action_creates_running_entry(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            "/api/time-entries/start/",
            {"workspace": self.workspace.id, "project": self.project.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_running_action_returns_current_timer(self):
        running = TimeEntry.objects.create(workspace=self.workspace, user=self.member, start_time=timezone.now())
        self.client.force_authenticate(user=self.member)
        response = self.client.get("/api/time-entries/running/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], running.id)

    def test_stop_action_ends_timer(self):
        running = TimeEntry.objects.create(workspace=self.workspace, user=self.member, start_time=self.start)
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            f"/api/time-entries/{running.id}/stop/",
            {"end_time": self.end.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_manual_entry_rejects_invalid_time_range(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            "/api/time-entries/",
            {"workspace": self.workspace.id, "start_time": self.end.isoformat(), "end_time": self.start.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_manual_entry_can_attach_tags(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            "/api/time-entries/",
            {
                "workspace": self.workspace.id,
                "project": self.project.id,
                "tags": [self.tag.id],
                "start_time": self.start.isoformat(),
                "end_time": self.end.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
