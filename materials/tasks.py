from celery import shared_task
from django.core.mail import send_mail

from config import settings
from materials.models import Course
from users.models import Subscription


@shared_task
def send_course_update_notification(course_id):
    course = Course.objects.get(id=course_id)
    subscribers = Subscription.objects.filter(course=course)
    for subscriber in subscribers:
        subject = f"Обновление курса {course.name}"
        message = f'Курс "{course.name}" был обновлен. Проверьте новые материалы!'
        recipient_list = [subscriber.user.email]

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=recipient_list,
            fail_silently=False,
        )
