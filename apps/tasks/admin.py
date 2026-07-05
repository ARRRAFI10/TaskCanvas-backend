from django.contrib import admin

from .models import Tag, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "priority", "due_date", "position")
    list_filter = ("status", "priority", "due_date")
    search_fields = ("title", "description")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "user")
    search_fields = ("name",)
