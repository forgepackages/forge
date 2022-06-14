from django.core.checks import Error
from django.urls import get_resolver, path
from django.views import View

from forge.standards.checks.urls import (
    check_resolver_admin_path,
    check_url_pattern_names,
    check_url_view_types,
)


def test_url_pattern_names():
    urlpatterns = [
        path("test/", lambda request: None, name="test-name"),
    ]
    errors = check_url_pattern_names(urlpatterns)
    assert errors == [
        Error(
            "URL name 'test-name' has a dash in it.",
            hint="Use underscores instead of dashes.",
            id="standards.E001",
        )
    ]

    urlpatterns = [
        path("test/", lambda request: None, name="test_name"),
    ]
    errors = check_url_pattern_names(urlpatterns)
    assert errors == []


def test_resolver_admin_path():
    resolver = get_resolver("tests.urls_fail")
    errors = check_resolver_admin_path(resolver)
    assert errors == [
        Error(
            "Do not use the standard /admin/ path",
            hint="Change the admin path to something less likely to be automatically scraped (ex. yourcompany-admin).",
            id="standards.E002",
        )
    ]

    resolver = get_resolver("tests.urls")
    errors = check_resolver_admin_path(resolver)
    assert errors == []


def test_url_view_types():
    class CBV(View):
        pass

    def fbv(request):
        pass

    urlpatterns = [
        path("fbv/", fbv),
    ]
    errors = check_url_view_types(urlpatterns)
    assert errors == [
        Error(
            "URL view 'tests.test_standards.test_url_view_types.<locals>.fbv' is function-based.",
            hint="Use class-based views instead of function-based views.",
            id="standards.E003",
            obj=fbv,
        )
    ]

    urlpatterns = [
        path("cbv/", CBV.as_view()),
    ]
    errors = check_url_view_types(urlpatterns)
    assert errors == []
