from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, serializers
from rest_framework.filters import OrderingFilter
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from materials.models import Course
from users.models import Payments, User, Subscription
from users.permissions import IsProfileOwner
from users.serializers import (
    PaymentSerializer,
    UserPrivateSerializer,
    UserPublicSerializer,
)
from users.services import (
    create_stripe_product,
    create_stripe_price,
    create_stripe_session,
)


@method_decorator(
    name="post",
    decorator=swagger_auto_schema(
        operation_description="Регистрация нового пользователя. Доступно без аутентификации."
    ),
)
class UserCreateAPIView(CreateAPIView):
    """API для регистрации пользователей."""

    queryset = User.objects.all()
    serializer_class = UserPrivateSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save(is_active=True)
        user.set_password(serializer.validated_data.get("password"))
        user.save()


docs_params = openapi.Parameter(
    "pk",
    openapi.IN_PATH,
    description="ID of the object to retrieve",
    type=openapi.TYPE_INTEGER,
    required=True,
)
responses = openapi.Response("Detail", UserPublicSerializer)


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        manual_parameters=[docs_params],
        responses={200: responses},
        operation_description="Просмотр профиля пользователя. "
        "Владелец профиля видит полную информацию, другие пользователи - только публичные данные.",
    ),
)
class UserRetrieveAPIView(RetrieveAPIView):
    """API для просмотра профиля пользователя."""

    queryset = User.objects.all()

    def get_serializer_class(self):
        # Используем get_object_or_404 для безопасного получения объекта
        if getattr(self, "swagger_fake_view", False):
            return UserPublicSerializer  # Для генерации схемы Swagger

        obj = self.get_object()
        if self.request.user == obj:
            return UserPrivateSerializer
        return UserPublicSerializer

    def get_object(self):
        if getattr(self, "swagger_fake_view", False):
            return None  # Для генерации схемы Swagger

        pk = self.kwargs.get("pk")
        return get_object_or_404(User, pk=pk)


@method_decorator(
    name="put",
    decorator=swagger_auto_schema(
        operation_description="Полное обновление профиля. Доступно только владельцу профиля."
    ),
)
@method_decorator(
    name="patch",
    decorator=swagger_auto_schema(
        operation_description="Частичное обновление профиля. Доступно только владельцу профиля."
    ),
)
class UserUpdateAPIView(UpdateAPIView):
    """API для обновления профиля пользователя."""

    serializer_class = UserPrivateSerializer
    permission_classes = [IsAuthenticated, IsProfileOwner]

    def get_object(self):
        return self.request.user


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_description="Получение списка пользователей. Доступно только администраторам."
    ),
)
class UserListAPIView(ListAPIView):
    """API для просмотра списка пользователей."""

    serializer_class = UserPublicSerializer
    queryset = User.objects.all()
    permission_classes = [IsAdminUser]


@method_decorator(
    name="delete",
    decorator=swagger_auto_schema(
        operation_description="Удаление профиля. Доступно только аутентифицированным пользователям для своего профиля."
    ),
)
class UserDeleteAPIView(DestroyAPIView):
    """API для удаления профиля пользователя."""

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="Получение списка платежей."),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Создание записи о платеже."),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Просмотр деталей платежа."),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Обновление записи о платеже."),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_description="Частичное обновление записи о платеже."
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Удаление записи о платеже."),
)
class PaymentViewSet(ModelViewSet):
    """ViewSet для работы с платежами."""

    queryset = Payments.objects.all()
    serializer_class = PaymentSerializer

    def perform_create(self, serializer):
        try:
            payment = serializer.save(user=self.request.user)
            product = create_stripe_product(payment.paid_course)
            price = create_stripe_price(payment.payment_amount, product.id)
            session = create_stripe_session(price.id)

            payment.stripe_product_id = product.id
            payment.stripe_price_id = price.id
            payment.stripe_session_id = session.id
            payment.stripe_payment_link = session.url
            payment.save()

        except Exception as e:
            print(f"Error during payment creation: {str(e)}")
            raise serializers.ValidationError(f"Ошибка при создании платежа: {str(e)}")

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["paid_course", "paid_lesson", "payment_method"]
    ordering_fields = ["payment_date"]


@method_decorator(
    name="post",
    decorator=swagger_auto_schema(
        operation_description="Добавление/удаление подписки на курс. "
        "При первом вызове создает подписку, при повторном - удаляет."
    ),
)
class SubscriptionAPIView(APIView):
    """API для управления подписками на курсы."""

    def post(self, *args, **kwargs):
        user = self.request.user
        course_id = self.request.data.get("course_id")
        if not course_id:
            return Response(
                {"error": "course_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        course_item = get_object_or_404(Course, id=course_id)

        subs_item, created = Subscription.objects.get_or_create(
            user=user,
            course=course_item,
            defaults={"user": user, "course": course_item},
        )

        if not created:
            subs_item.delete()
            message = "Подписка удалена"
        else:
            message = "Подписка добавлена"

        return Response({"message": message}, status=status.HTTP_200_OK)
