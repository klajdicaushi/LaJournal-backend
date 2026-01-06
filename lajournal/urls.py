from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from project.api import api


def healthz(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/", api.urls),
    path("admin/", admin.site.urls),
    path("healthz", healthz),
]
