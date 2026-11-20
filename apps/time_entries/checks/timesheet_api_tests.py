from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.time_entries.models import TimeEntry
from apps.users.models import User
from apps.workspaces.models import Workspace


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TimesheetApiChecks(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile="09125550001", password="pass12345")
        self.workspace = Workspace.objects.create(name="Team", owner=self.user)
        self.start = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        self.end = self.start + timedelta(hours=1)
        self.entry = TimeEntry.objects.create(
            workspace=self.workspace,
            user=self.user,
            description="Work",
            start_time=self.start,
            end_time=self.end,
        )

    def test_list_returns_groups(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("groups", response.json())

    def test_grouped_endpoint_returns_groups(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/grouped/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("groups", response.json())

    def test_total_ms_uses_duration(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/")
        group = response.json()["groups"][0]
        self.assertEqual(group["total_ms"], 3600 * 1000)

    def test_empty_timesheet_returns_empty_groups(self):
        TimeEntry.objects.filter(user=self.user).delete()
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/")
        self.assertEqual(response.json()["groups"], [])

    def test_group_key_is_entry_date(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/time-entries/")
        self.assertEqual(response.json()["groups"][0]["key"], self.start.date().isoformat())
