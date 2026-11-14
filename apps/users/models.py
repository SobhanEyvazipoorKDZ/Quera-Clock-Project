from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def _create_user(self, mobile, password=None, **extra_fields):
        if not mobile:
            raise ValueError("The mobile number must be provided.")

        user = self.model(mobile=mobile, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, mobile, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(
            mobile=mobile,
            password=password,
            **extra_fields,
        )

    def create_superuser(self, mobile, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(
            mobile=mobile,
            password=password,
            **extra_fields,
        )


class User(AbstractBaseUser, PermissionsMixin):
    mobile = models.CharField(max_length=20, unique=True)

    email = models.EmailField(blank=True)

    first_name = models.CharField(max_length=150, blank=True)

    last_name = models.CharField(max_length=150, blank=True)

    description = models.TextField(blank=True)

    birth_date = models.DateField(blank=True, null=True)

    profile_picture = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "mobile"

    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["first_name", "last_name", "mobile"]

    @property
    def full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.mobile

    def __str__(self):
        return self.full_name
