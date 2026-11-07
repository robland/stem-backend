from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["pseudo", "phone", "level", "is_staff", "date_joined"]
    list_filter = ["level", "is_staff", "is_active"]
    search_fields = ["pseudo", "phone"]
    fieldsets = [
        (None, {"fields": ["phone", "pseudo", "password"]}),
        ("Scolarité", {"fields": ["level", "serie"]}),
        ("Droits", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["phone", "pseudo", "password1", "password2"]}),
    ]
