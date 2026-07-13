from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.tasks.urls")),
    path("api/", include("apps.annotations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Media must be served *through* Django so CorsMiddleware can attach
    # Access-Control-Allow-Origin. The canvas loads images with
    # crossOrigin="anonymous" (Konva's filters need an untainted canvas to call
    # getImageData), and the browser drops a cross-origin image that comes back
    # without that header. A host-level static mapping for /media/ would bypass
    # Django entirely and strip it — so don't add one.
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
