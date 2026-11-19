from django.core.cache import cache
from django.http import StreamingHttpResponse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.notifications.models import Notification
from apps.users.models import User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SSEAPIChecks(APITestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            mobile="09128880000", password="StrongPass123"
        )

    def test_stream_token_requires_authentication(self):
        response = self.client.post("/api/notifications/stream-token/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stream_token_is_created_for_current_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/notifications/stream-token/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            cache.get(f"notifications:sse:{response.data['token']}"), str(self.user.id)
        )

    def test_stream_rejects_invalid_token(self):
        response = self.client.get(
            "/api/notifications/stream/?token=bad", HTTP_ACCEPT="text/event-stream"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stream_returns_streaming_response_for_valid_token(self):
        self.client.force_authenticate(self.user)
        token = self.client.post("/api/notifications/stream-token/").data["token"]
        response = self.client.get(
            f"/api/notifications/stream/?token={token}", HTTP_ACCEPT="text/event-stream"
        )
        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertIn("text/event-stream", response["Content-Type"])

    def test_stream_sends_notification_event(self):
        Notification.objects.create(user=self.user, title="Live")
        self.client.force_authenticate(self.user)
        token = self.client.post("/api/notifications/stream-token/").data["token"]
        response = self.client.get(
            f"/api/notifications/stream/?token={token}", HTTP_ACCEPT="text/event-stream"
        )
        chunk = next(response.streaming_content).decode("utf-8")
        self.assertIn("event: notification", chunk)
        self.assertIn("Live", chunk)
