from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import generic

from .forms import SignupForm


class SignupView(generic.CreateView):
    form_class = SignupForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("/")
        return super().dispatch(request, *args, **kwargs)
