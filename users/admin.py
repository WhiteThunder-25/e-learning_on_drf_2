from django.contrib import admin
from django.contrib.admin import ModelAdmin

from users.models import User, Payments


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_filter = ("id", "email")


@admin.register(Payments)
class PaymentsAdmin(ModelAdmin):
    pass
