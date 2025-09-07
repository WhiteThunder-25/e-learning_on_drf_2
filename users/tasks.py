from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.contrib.auth import get_user_model


@shared_task
def checking_inactive_users():
    User = get_user_model()
    inactive_period = timezone.now() - timedelta(days=30)
    inactive_users = User.objects.filter(
        last_login__lt=inactive_period,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    count = inactive_users.update(is_active=False)
    return f"Заблокировано {count} неактивных пользователей"
