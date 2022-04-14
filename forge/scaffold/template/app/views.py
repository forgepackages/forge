from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from forge.views.mixins import HTMLTitleMixin


class BaseLoggedInView(LoginRequiredMixin, HTMLTitleMixin):
    html_title_suffix = " | Built with Forge"


class HomeView(BaseLoggedInView, TemplateView):
    html_title = "Home"
    template_name = "home.html"
