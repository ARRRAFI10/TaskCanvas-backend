from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AnnotationDestroyView, AnnotationListCreateView, ImageViewSet

router = SimpleRouter()
router.register("images", ImageViewSet, basename="image")

urlpatterns = [
    path(
        "images/<int:image_id>/annotations/",
        AnnotationListCreateView.as_view(),
        name="image-annotations",
    ),
    path("annotations/<int:pk>/", AnnotationDestroyView.as_view(), name="annotation-detail"),
    *router.urls,
]
