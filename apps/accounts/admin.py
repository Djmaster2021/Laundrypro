from django.contrib import admin

from .models import UserCredentialPolicy


@admin.register(UserCredentialPolicy)
class UserCredentialPolicyAdmin(admin.ModelAdmin):
    list_display = ("user", "password_changed_at", "require_password_change", "updated_at")
    list_filter = ("require_password_change",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
