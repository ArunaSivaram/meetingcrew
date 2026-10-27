from django.db import models


class Participant(models.Model):
    """A person the agents can assign action items to."""

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    github_username = models.CharField(max_length=39)
    aliases = models.TextField(
        blank=True,
        help_text="Comma-separated nicknames the agents may see in notes (e.g. 'Alex, A.J.').",
    )

    def __str__(self) -> str:
        return f"{self.name} (@{self.github_username})"


class MeetingRun(models.Model):
    """One attempt at processing a block of meeting notes."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    created_at = models.DateTimeField(auto_now_add=True)
    repo = models.CharField(max_length=140, help_text="GitHub repo in the form owner/repo.")
    notes = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)
    summary = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"MeetingRun #{self.pk} ({self.repo}, {self.status})"


class ActionItem(models.Model):
    """A single task extracted from a MeetingRun."""

    run = models.ForeignKey(
        MeetingRun, on_delete=models.CASCADE, related_name="action_items"
    )
    task = models.TextField()
    owner = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="action_items",
    )
    due_date = models.DateField(null=True, blank=True)
    issue_url = models.URLField(blank=True)
    issue_number = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        owner_name = self.owner.name if self.owner else "unassigned"
        return f"{self.task[:50]} → {owner_name}"
