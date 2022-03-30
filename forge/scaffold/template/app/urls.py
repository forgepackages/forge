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
import views
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
