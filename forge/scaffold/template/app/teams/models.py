from django.db import models
from forge.models import TimestampModel, UUIDModel


class Team(TimestampModel, UUIDModel):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(
        "users.User", related_name="teams", through="TeamMembership"
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class TeamRoles(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    MEMBER = "MEMBER", "Member"


class TeamMembership(TimestampModel, UUIDModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(
        max_length=20, choices=TeamRoles.choices, default=TeamRoles.ADMIN
    )

    class Meta:
        unique_together = ("team", "user")

    def __str__(self):
        return f"{self.user}: {self.get_role_display()} on {self.team}"
