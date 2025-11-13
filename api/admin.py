from django.contrib import admin

from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "created_at")
    search_fields = ("username", "email")
    readonly_fields = ("created_at", "updated_at")
