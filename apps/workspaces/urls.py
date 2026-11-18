from django.urls import path

from . import views

app_name = "workspaces"

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("status/", views.StatusView.as_view(), name="status"),
]
