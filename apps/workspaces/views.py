from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from apps.clients.models import Client
from apps.contact_notes.forms import ContactNoteForm
from apps.projects.models import Project
from apps.tags.models import Tag
from apps.time_entries.models import TimeEntry

from .models import Workspace


class LandingView(TemplateView):
    template_name = "pages/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workspace_count"] = Workspace.objects.count()
        context["project_count"] = Project.objects.count()
        return context


class StatusView(TemplateView):
    template_name = "pages/status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workspace_count"] = Workspace.objects.count()
        context["client_count"] = Client.objects.count()
        context["project_count"] = Project.objects.count()
        context["tag_count"] = Tag.objects.count()
        context["time_entry_count"] = TimeEntry.objects.count()
        context["running_timer_count"] = TimeEntry.objects.running().count()
        return context


class AboutView(FormView):
    template_name = "pages/about.html"
    form_class = ContactNoteForm
    success_url = reverse_lazy("workspaces:about")

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request, "Thanks for your note — we'll get back to you soon."
        )
        return super().form_valid(form)


class DashboardPreviewView(LoginRequiredMixin, TemplateView):
    template_name = "pages/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["workspaces"] = Workspace.objects.visible_to(user).annotate(
            member_count=Count("memberships")
        )
        context["running_timer_count"] = (
            TimeEntry.objects.visible_to(user).running().count()
        )
        context["recent_entries"] = (
            TimeEntry.objects.visible_to(user)
            .select_related("project", "workspace")
            .order_by("-start_time")[:5]
        )
        return context
