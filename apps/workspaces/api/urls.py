from rest_framework.routers import DefaultRouter

from apps.workspaces.api.views import WorkspaceViewSet

router = DefaultRouter()
router.register("", WorkspaceViewSet, basename="workspaces")
urlpatterns = router.urls
