from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from materials.models import Course, Lesson
from materials.paginations import CustomPagination
from materials.serializers import (
    CourseDetailSerializer,
    CourseSerializer,
    LessonSerializer,
)
from users.permissions import IsModerator, IsOwner
from materials.tasks import send_course_update_notification


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_description="Получение списка курсов. "
        "Модераторы видят все курсы, обычные пользователи - только свои."
    ),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_description="Создание курса. Доступно только аутентифицированным пользователям, "
        "не являющимся модераторами. Автоматически назначает создателя владельцем."
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_description="Просмотр детальной информации о курсе. Доступно только аутентифицированным пользователям, "
        "являющимся модераторами или владельцами курса."
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_description="Полное обновление курса. Доступно только аутентифицированным пользователям, "
        "являющимся модераторами или владельцами курса."
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_description="Частичное обновление курса. Доступно только аутентифицированным пользователям, "
        "являющимся модераторами или владельцами курса."
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_description="Удаление курса. Доступно только аутентифицированным пользователям, "
        "являющимся владельцами курса или не являющимся модераторами."
    ),
)
class CourseViewSet(ModelViewSet):
    """ViewSet для работы с курсами. Предоставляет полный CRUD функционал."""

    queryset = Course.objects.all()
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseSerializer

    def perform_create(self, serializer):
        course = serializer.save(owner=self.request.user)
        course.save()

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = [~IsModerator, IsAuthenticated]
        elif self.action in ["update", "retrieve", "partial_update"]:
            self.permission_classes = [IsModerator | IsOwner]
        elif self.action == "destroy":
            self.permission_classes = [IsOwner | ~IsModerator]
        return super().get_permissions()

    def perform_update(self, serializer):
        instance = serializer.save()
        time_threshold = timezone.now() - timedelta(hours=4)
        if instance.last_update < time_threshold:
            send_course_update_notification.delay(instance.id)


@method_decorator(
    name="post",
    decorator=swagger_auto_schema(
        operation_description="Создание урока. Доступно только аутентифицированным пользователям, "
        "не являющимся модераторами. Автоматически назначает создателя владельцем."
    ),
)
class LessonCreateApiView(CreateAPIView):
    """API для создания уроков."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [~IsModerator, IsAuthenticated]

    def perform_create(self, serializer):
        lesson = serializer.save(owner=self.request.user)
        lesson.save()


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_description="Получение списка уроков. Модераторы видят все уроки, обычные пользователи - только свои."
    ),
)
class LessonListApiView(ListAPIView):
    """API для получения списка уроков."""

    serializer_class = LessonSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.user.groups.filter(name="moderators").exists():
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=self.request.user)


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_description="Просмотр детальной информации об уроке. "
        "Доступно только аутентифицированным пользователям, "
        "являющимся модераторами или владельцами урока."
    ),
)
class LessonRetrieveApiView(RetrieveAPIView):
    """API для просмотра урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsModerator | IsOwner]


@method_decorator(
    name="put",
    decorator=swagger_auto_schema(
        operation_description="Полное обновление урока. Доступно только аутентифицированным пользователям, "
        "являющимся модераторами или владельцами урока."
    ),
)
@method_decorator(
    name="patch",
    decorator=swagger_auto_schema(
        operation_description="Частичное обновление урока. Доступно только аутентифицированным пользователям, "
        "являющимся модераторами или владельцами урока."
    ),
)
class LessonUpdateApiView(UpdateAPIView):
    """API для обновления урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsModerator | IsOwner]

    def perform_update(self, serializer):
        instance = serializer.save()
        course = instance.course
        time_threshold = timezone.now() - timedelta(hours=4)
        if course.last_update < time_threshold:
            course.last_update = timezone.now()
            course.save()
            send_course_update_notification.delay(course.id)


@method_decorator(
    name="delete",
    decorator=swagger_auto_schema(
        operation_description="Удаление урока. Доступно только аутентифицированным пользователям, "
        "являющимся владельцами урока или не являющимся модераторами."
    ),
)
class LessonDestroyApiView(DestroyAPIView):
    """API для удаления урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated & (IsOwner | ~IsModerator)]
