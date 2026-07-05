import re

from rest_framework import serializers

from .models import Annotation, Image

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


class ImageSerializer(serializers.ModelSerializer):
    annotation_count = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = (
            "id",
            "file",
            "original_name",
            "width",
            "height",
            "annotation_count",
            "uploaded_at",
        )
        read_only_fields = ("id", "original_name", "width", "height", "uploaded_at")

    def get_annotation_count(self, obj):
        count = getattr(obj, "annotation_count", None)
        return count if count is not None else obj.annotations.count()

    def validate_file(self, value):
        if value.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("Images must be 10 MB or smaller.")
        # DRF's ImageField has already opened the upload with Pillow and attached it.
        image_format = value.image.format if getattr(value, "image", None) else None
        if image_format not in ALLOWED_FORMATS:
            raise serializers.ValidationError("Only JPEG, PNG, and WebP images are supported.")
        return value

    def create(self, validated_data):
        upload = validated_data["file"]
        return Image.objects.create(
            user=self.context["request"].user,
            file=upload,
            original_name=upload.name,
            width=upload.image.width,
            height=upload.image.height,
        )


class AnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ("id", "image", "label", "color", "points", "created_at")
        read_only_fields = ("id", "image", "created_at")

    def validate_color(self, value):
        if not HEX_COLOR.fullmatch(value):
            raise serializers.ValidationError("Color must be a #RRGGBB hex value.")
        return value

    def validate_points(self, value):
        if not isinstance(value, list) or len(value) < 3:
            raise serializers.ValidationError("A polygon needs at least 3 vertices.")
        for vertex in value:
            if not isinstance(vertex, (list, tuple)) or len(vertex) != 2:
                raise serializers.ValidationError("Each vertex must be an [x, y] pair.")
            if not all(
                isinstance(coord, (int, float)) and not isinstance(coord, bool)
                for coord in vertex
            ):
                raise serializers.ValidationError("Vertex coordinates must be numbers.")
            if not all(0 <= coord <= 1 for coord in vertex):
                raise serializers.ValidationError(
                    "Coordinates must be normalized to the 0–1 range."
                )
        return value
