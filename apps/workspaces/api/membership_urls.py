from rest_framework.routers import DefaultRouter

from apps.workspaces.api.views import WorkspaceMembershipViewSet

router = DefaultRouter()
router.register("", WorkspaceMembershipViewSet, basename="memberships")
urlpatterns = router.urls
