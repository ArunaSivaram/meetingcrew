from django.contrib import admin

from .models import ActionItem, MeetingRun, Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "github_username", "aliases")
    search_fields = ("name", "email", "github_username", "aliases")


@admin.register(MeetingRun)
class MeetingRunAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "repo", "status")
    list_filter = ("status", "repo")
    search_fields = ("repo", "notes", "summary")
    readonly_fields = ("created_at",)


@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "task_preview", "owner", "due_date", "issue_number")
    list_filter = ("owner", "due_date")
    search_fields = ("task", "issue_url")

    @admin.display(description="task")
    def task_preview(self, obj: ActionItem) -> str:
        return obj.task[:60] + ("…" if len(obj.task) > 60 else "")
