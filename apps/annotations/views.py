from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from .models import Annotation, Image
from .serializers import AnnotationSerializer, ImageSerializer


class ImageViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ImageSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user).annotate(
            annotation_count=Count("annotations")
        )

    def perform_destroy(self, instance):
        instance.file.delete(save=False)
        instance.delete()


class AnnotationListCreateView(generics.ListCreateAPIView):
    serializer_class = AnnotationSerializer

    def get_image(self):
        return get_object_or_404(Image, pk=self.kwargs["image_id"], user=self.request.user)

    def get_queryset(self):
        return Annotation.objects.filter(image=self.get_image())

    def perform_create(self, serializer):
        serializer.save(image=self.get_image())


class AnnotationDestroyView(generics.DestroyAPIView):
    def get_queryset(self):
        return Annotation.objects.filter(image__user=self.request.user)
