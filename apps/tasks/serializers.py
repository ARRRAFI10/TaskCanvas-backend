from django.db.models import Max
from rest_framework import serializers

from .models import Tag, Task


class TagListField(serializers.ListField):
    """Tags travel as plain strings over the API; rows are created lazily per user."""

    child = serializers.CharField(max_length=50)

    def to_representation(self, value):
        return [tag.name for tag in value.all()]


class TaskSerializer(serializers.ModelSerializer):
    tags = TagListField(required=False)

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "status",
            "priority",
            "due_date",
            "tags",
            "position",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "position", "created_at", "updated_at")

    def create(self, validated_data):
        tag_names = validated_data.pop("tags", [])
        user = self.context["request"].user
        validated_data["position"] = self._next_position(
            user, validated_data["due_date"], validated_data.get("status", Task.Status.TODO)
        )
        task = Task.objects.create(user=user, **validated_data)
        if tag_names:
            task.tags.set(self._resolve_tags(user, tag_names))
        return task

    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tags", None)
        user = self.context["request"].user

        # Edits that relocate the task to another column/board append it at the end
        # there; in-column reordering stays the move endpoint's job.
        new_status = validated_data.get("status", instance.status)
        new_due = validated_data.get("due_date", instance.due_date)
        if new_status != instance.status or new_due != instance.due_date:
            validated_data["position"] = self._next_position(
                user, new_due, new_status, exclude_pk=instance.pk
            )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tag_names is not None:
            instance.tags.set(self._resolve_tags(user, tag_names))
        return instance

    @staticmethod
    def _next_position(user, due_date, status, exclude_pk=None):
        column = Task.objects.filter(user=user, due_date=due_date, status=status)
        if exclude_pk is not None:
            column = column.exclude(pk=exclude_pk)
        last = column.aggregate(m=Max("position"))["m"]
        return 0 if last is None else last + 1

    @staticmethod
    def _resolve_tags(user, names):
        seen = set()
        tags = []
        for name in names:
            clean = name.strip()
            if not clean or clean.lower() in seen:
                continue
            seen.add(clean.lower())
            tags.append(Tag.objects.get_or_create(user=user, name=clean)[0])
        return tags


class TaskMoveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.Status.choices)
    position = serializers.IntegerField(min_value=0)
