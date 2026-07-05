from datetime import date

from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Task
from .serializers import TaskMoveSerializer, TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        queryset = Task.objects.filter(user=self.request.user).prefetch_related("tags")
        date_param = self.request.query_params.get("date")
        if date_param:
            try:
                selected = date.fromisoformat(date_param)
            except ValueError:
                raise serializers.ValidationError(
                    {"date": ["Enter a valid date in YYYY-MM-DD format."]}
                ) from None
            queryset = queryset.filter(due_date=selected)
        return queryset

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        task = self.get_object()
        serializer = TaskMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        new_index = serializer.validated_data["position"]

        with transaction.atomic():
            board = Task.objects.filter(user=request.user, due_date=task.due_date)
            source = list(
                board.filter(status=task.status).exclude(pk=task.pk).order_by("position")
            )
            if new_status == task.status:
                target = source
            else:
                target = list(board.filter(status=new_status).order_by("position"))

            target.insert(min(new_index, len(target)), task)
            task.status = new_status

            # Dense renumber of every affected column; the moved task is saved even
            # when only its status changed.
            changed = {task.pk: task}
            for column in (target,) if source is target else (target, source):
                for index, item in enumerate(column):
                    if item.position != index:
                        item.position = index
                        changed[item.pk] = item
            Task.objects.bulk_update(changed.values(), ["position", "status"])

        return Response(self.get_serializer(task).data)
