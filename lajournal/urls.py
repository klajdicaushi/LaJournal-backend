from django.urls import path

from project.api import api

urlpatterns = [
    path("api/", api.urls),
]
