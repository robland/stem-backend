from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, password=None, **extra_field):
        if not username:
            raise ValueError('Username is required')
        user = self.model(username=username, **extra_field)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, username, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(username, password=password, **extra_fields)


class CustomUser(AbstractUser):
    phone = models.CharField(max_length=25, unique=True)
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['phone']
    objects = UserManager()


