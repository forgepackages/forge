import os

from django.apps import apps
from django.conf import settings
from django.core.checks import Error, Tags, register
from django.urls.exceptions import Resolver404


@register("standards", Tags.urls)
def check_urls(app_configs, **kwargs):
    errors = []

    if not getattr(settings, "ROOT_URLCONF", None):
        return []

    from django.urls import get_resolver

    resolver = get_resolver()
    url_patterns = getattr(resolver, "url_patterns", [])

    url_patterns = _all_first_party_url_patterns(url_patterns)

    errors += check_resolver_admin_path(resolver)
    errors += check_url_pattern_names(url_patterns)

    return errors


def check_url_pattern_names(url_patterns):
    errors = []
    for pattern in url_patterns:
        name = getattr(pattern, "name", None)
        if name and "-" in name:
            errors.append(
                Error(
                    f"URL name '{name}' has a dash in it.",
                    hint="Use underscores instead of dashes.",
                    id="standards.E001",
                )
            )

    return errors


def check_resolver_admin_path(resolver):
    try:
        resolved = resolver.resolve("/admin/")
    except Resolver404:
        return []

    if resolved.view_name == "admin:index":
        return [
            Error(
                f"Do not use the standard /admin/ path",
                hint="Change the admin path to something less likely to be automatically scraped (ex. yourcompany-admin).",
                id="standards.E002",
            )
        ]

    return []


def check_url_view_types(url_patterns):
    errors = []
    for pattern in url_patterns:
        if not hasattr(pattern.callback, "view_class"):
            errors.append(
                Error(
                    f"URL view '{pattern.lookup_str}' is function-based.",
                    hint="Use class-based views instead of function-based views.",
                    obj=pattern.callback,
                    id="standards.E003",
                )
            )

    return errors


def _all_first_party_url_patterns(url_patterns):
    for pattern in url_patterns:
        # Only care about first party apps - things we have control over
        app_name = getattr(pattern, "app_name", None)
        if app_name and _is_third_party_app(app_name):
            continue

        included_patterns = getattr(pattern, "url_patterns", None)
        if included_patterns:
            url_patterns += _all_first_party_url_patterns(included_patterns)

    return url_patterns


def _is_third_party_app(app_name):
    """Assume an app is third-party if it is in site-packages"""
    cfg = apps.get_app_config(app_name)
    app_path = cfg.path

    head, tail = os.path.split(app_path)
    while tail != "":
        if tail == "site-packages":
            return True
        head, tail = os.path.split(head)

    return False
