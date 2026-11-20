from rest_framework.routers import DefaultRouter

from apps.time_entries.api.views import TimeEntryViewSet

router = DefaultRouter()
router.register("", TimeEntryViewSet, basename="time_entries")
urlpatterns = router.urls
