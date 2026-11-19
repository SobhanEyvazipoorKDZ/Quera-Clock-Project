from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.workspaces.urls")),
    path("auth/", include("apps.users.urls")),
    path("api/users/", include("apps.users.api.urls")),
    path("api/notifications/", include("apps.notifications.api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
