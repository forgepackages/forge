from django.contrib.auth.models import AbstractUser
from django.db import models
from forge.models import UUIDModel


class User(AbstractUser, UUIDModel):
    email = models.EmailField(unique=True)
