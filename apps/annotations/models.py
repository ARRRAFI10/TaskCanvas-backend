from django.conf import settings
from django.db import models


class Image(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="images"
    )
    file = models.ImageField(upload_to="uploads/%Y/%m/")
    original_name = models.CharField(max_length=255)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return self.original_name


class Annotation(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="annotations")
    label = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=7, default="#22d3ee")
    # Polygon vertices as [[x, y], ...] with every coordinate normalized to 0..1
    # of the image dimensions, so drawings are resolution-independent.
    points = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.label or f"Polygon #{self.pk}"
