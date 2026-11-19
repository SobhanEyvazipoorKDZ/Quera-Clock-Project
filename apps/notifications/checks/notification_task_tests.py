from django.test import override_settings
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.notifications.tasks import create_notification_task
from apps.users.models import User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class NotificationTaskChecks(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile="09129991111", password="StrongPass123")

    def test_task_creates_notification(self):
        create_notification_task(self.user.id, "Task title", "Task body")
        self.assertTrue(Notification.objects.filter(user=self.user, title="Task title").exists())

    def test_task_returns_notification_id(self):
        notification_id = create_notification_task(self.user.id, "Task id")
        self.assertTrue(str(notification_id).isdigit())

    def test_task_stores_body(self):
        notification_id = create_notification_task(self.user.id, "Body", "Message")
        self.assertEqual(Notification.objects.get(id=notification_id).body, "Message")

    def test_task_delay_runs_in_development_eager_mode(self):
        result = create_notification_task.delay(self.user.id, "Delayed", "Message")
        if hasattr(result, "get"):
            result.get()
        self.assertTrue(Notification.objects.filter(title="Delayed").exists())

    def test_task_rejects_unknown_user(self):
        with self.assertRaises(User.DoesNotExist):
            create_notification_task(999999, "Missing")
