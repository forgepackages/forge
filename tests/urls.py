from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("dropseed-admin/", admin.site.urls),
]
