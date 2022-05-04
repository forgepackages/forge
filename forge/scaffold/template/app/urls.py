"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import django.views.defaults
import views
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from users.views import MyAccountView, SignupView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("signup/", SignupView.as_view(), name="signup"),
    path("my-account/", MyAccountView.as_view(), name="my_account"),
    path("", include("django.contrib.auth.urls")),
    path("teams/", include("teams.urls")),
    path("", views.HomeView.as_view(), name="home"),
]

# Make the error pages viewable in development
if settings.DEBUG:
    urlpatterns += [
        path(
            "400/",
            lambda request: django.views.defaults.bad_request(
                request, Exception("400 error")
            ),
        ),
        path(
            "403/",
            lambda request: django.views.defaults.permission_denied(
                request, Exception("403 error")
            ),
        ),
        path(
            "404/",
            lambda request: django.views.defaults.page_not_found(
                request, Exception("404 error")
            ),
        ),
        path("500/", django.views.defaults.server_error),
    ]
