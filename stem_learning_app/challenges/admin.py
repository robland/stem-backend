from django.contrib import admin

from .models import Challenge, ChallengeReport


class ChallengeReportInline(admin.TabularInline):
    model = ChallengeReport
    extra = 0
    readonly_fields = ["reporter", "reason", "created_at"]


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ["code", "exercise", "author", "visibility", "status", "created_at"]
    list_filter = ["status", "visibility"]
    search_fields = ["code"]
    readonly_fields = ["moderation_reasons", "moderation_prompt_id"]
    inlines = [ChallengeReportInline]
    actions = ["publish", "reject"]

    @admin.action(description="Rendre actif (après relecture)")
    def publish(self, request, queryset):
        queryset.update(status=Challenge.Status.ACTIVE)

    @admin.action(description="Refuser")
    def reject(self, request, queryset):
        queryset.update(status=Challenge.Status.REJECTED)


@admin.register(ChallengeReport)
class ChallengeReportAdmin(admin.ModelAdmin):
    list_display = ["challenge", "reason", "created_at"]
    list_filter = ["reason"]
