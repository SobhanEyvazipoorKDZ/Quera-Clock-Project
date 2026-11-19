try:
    from celery import shared_task
except Exception:

    def shared_task(func=None, **kwargs):
        def decorator(inner):
            inner.delay = inner
            return inner

        return decorator(func) if func else decorator


from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import create_notification


@shared_task
def create_notification_task(user_id, title, body=""):
    from apps.users.models import User

    user = User.objects.get(pk=user_id)
    notification = create_notification(user, title, body)
    return str(notification.pk)


@shared_task
def cleanup_read_notifications(days=30):
    cutoff = timezone.now() - timezone.timedelta(days=days)
    deleted = Notification.objects.filter(is_read=True, updated_at__lt=cutoff).delete()
    return deleted
