from rest_framework.routers import DefaultRouter

from apps.tags.api.views import TagViewSet

router = DefaultRouter()
router.register("", TagViewSet, basename="tags")
urlpatterns = router.urls
