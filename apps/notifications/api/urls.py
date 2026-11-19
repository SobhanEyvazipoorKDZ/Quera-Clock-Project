from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.notifications.api.views import (
    NotificationListAPIView,
    NotificationSeenAPIView,
    NotificationSeenAllAPIView,
    NotificationViewSet,
)

router = DefaultRouter()
router.register("", NotificationViewSet, basename="notifications")

urlpatterns = [
    path("list/", NotificationListAPIView.as_view(), name="list"),
    path("seen/", NotificationSeenAPIView.as_view(), name="seen"),
    path("seen/all/", NotificationSeenAllAPIView.as_view(), name="seen-all"),
    *router.urls,
]
