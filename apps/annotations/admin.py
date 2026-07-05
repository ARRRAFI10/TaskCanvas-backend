from django.contrib import admin

from .models import Annotation, Image


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("original_name", "user", "width", "height", "uploaded_at")
    search_fields = ("original_name",)


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "image", "color", "created_at")
    list_filter = ("created_at",)
