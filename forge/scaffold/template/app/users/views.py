from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import generic
from teams.models import Team, TeamMembership, TeamRoles
from views import BaseLoggedInView

from .forms import SignupForm
from .models import User


class SignupView(generic.CreateView):
    html_title = "Sign up"
    form_class = SignupForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("/")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()

        # Create a "Personal" team for the new user
        team = Team.objects.create(name=user.username)
        TeamMembership.objects.create(user=user, team=team, role=TeamRoles.ADMIN)

        return super().form_valid(form)


class MyAccountView(BaseLoggedInView, generic.UpdateView):
    html_title = "My account"
    model = User
    fields = ("username", "email", "first_name", "last_name")
    success_url = "."

    def get_object(self, queryset=None):
        return self.request.user
