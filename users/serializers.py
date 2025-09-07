from rest_framework import serializers

from materials.models import Course, Lesson
from users.models import Payments, User, Subscription


class PaymentSerializer(serializers.ModelSerializer):
    paid_course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), required=False, allow_null=True
    )
    paid_lesson = serializers.PrimaryKeyRelatedField(
        queryset=Lesson.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Payments
        fields = "__all__"
        read_only_fields = (
            "user",
            "payment_date",
            "stripe_product_id",
            "stripe_price_id",
            "stripe_session_id",
            "stripe_payment_link",
        )

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user

        if not validated_data.get("paid_course") and not validated_data.get(
            "paid_lesson"
        ):
            raise serializers.ValidationError("Необходимо указать либо курс, либо урок")

        return super().create(validated_data)


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "phone", "city", "avatar"]
        read_only_fields = fields


class UserPrivateSerializer(serializers.ModelSerializer):
    payment_history = serializers.SerializerMethodField()

    @staticmethod
    def get_payment_history(obj):
        payments = obj.payments.all().order_by("-payment_date")
        return PaymentSerializer(payments, many=True).data

    class Meta:
        model = User
        fields = ["email", "password", "phone", "city", "avatar", "payment_history"]
        extra_kwargs = {"password": {"write_only": True}}


class SubscriptionSerializer(serializers.ModelSerializer):
    course = serializers.SlugRelatedField(
        slug_field="name", queryset=Course.objects.all()
    )

    class Meta:
        model = Subscription
        fields = "__all__"
