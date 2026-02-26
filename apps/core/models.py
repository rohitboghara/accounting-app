from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_STAFF = 'staff'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_STAFF, 'Staff'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STAFF)
    phone = models.CharField(max_length=15, blank=True)

    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
