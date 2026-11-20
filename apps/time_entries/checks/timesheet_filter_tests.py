from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.projects.models import Project
from apps.time_entries.models import TimeEntry
from apps.users.models import User
from apps.workspaces.models import Workspace


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TimesheetFilterChecks(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile="09126660001", password="pass12345")
        self.workspace = Workspace.objects.create(name="Team", owner=self.user)
        self.project = Project.objects.create(workspace=self.workspace, name="Website")
        self.start = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        self.entry = TimeEntry.objects.create(
            workspace=self.workspace,
            user=self.user,
            project=self.project,
            description="Backend work",
            start_time=self.start,
            end_time=self.start + timedelta(hours=1),
        )

    def test_project_filter_returns_project_entries(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/", {"project": self.project.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_items"], 1)

    def test_search_filter_matches_description(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/", {"search": "Backend"})
        self.assertEqual(response.json()["total_items"], 1)

    def test_status_ended_filter_returns_ended_entries(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/", {"status": "ended"})
        self.assertEqual(response.json()["total_items"], 1)

    def test_started_before_filter_can_return_empty_result(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/", {"started_before": (self.start - timedelta(days=1)).isoformat()})
        self.assertEqual(response.json()["groups"], [])

    def test_ordering_start_time_keeps_grouped_payload(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/", {"ordering": "start_time"})
        self.assertIn("groups", response.json())
