from django.conf import settings
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.notifications.models import Notification
from apps.notifications.tasks import cleanup_read_notifications
from apps.users.models import User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CeleryBeatChecks(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(mobile="09120008888", password="StrongPass123")

    def test_cleanup_task_soft_deletes_old_read_notifications(self):
        notification = Notification.objects.create(user=self.user, title="Old", is_read=True)
        Notification.all_objects.filter(id=notification.id).update(
            updated_at=timezone.now() - timezone.timedelta(days=40)
        )
        cleanup_read_notifications(days=30)
        notification.refresh_from_db()
        self.assertTrue(notification.is_deleted)

    def test_cleanup_task_keeps_unread_notifications(self):
        notification = Notification.objects.create(user=self.user, title="Unread", is_read=False)
        Notification.all_objects.filter(id=notification.id).update(
            updated_at=timezone.now() - timezone.timedelta(days=40)
        )
        cleanup_read_notifications(days=30)
        notification.refresh_from_db()
        self.assertFalse(notification.is_deleted)

    def test_cleanup_task_returns_deleted_count(self):
        notification = Notification.objects.create(user=self.user, title="Old", is_read=True)
        Notification.all_objects.filter(id=notification.id).update(
            updated_at=timezone.now() - timezone.timedelta(days=40)
        )
        self.assertEqual(cleanup_read_notifications(days=30), 1)

    def test_beat_schedule_is_registered(self):
        self.assertIn("cleanup-read-notifications", settings.CELERY_BEAT_SCHEDULE)

    def test_beat_schedule_points_to_cleanup_task(self):
        schedule = settings.CELERY_BEAT_SCHEDULE["cleanup-read-notifications"]
        self.assertEqual(schedule["task"], "apps.notifications.tasks.cleanup_read_notifications")
