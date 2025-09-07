from rest_framework import serializers


def validate_link(value):
    if "youtube" not in value.lower():
        raise serializers.ValidationError(
            "Добавить ссылку на данный источник невозможно"
        )
