import logging

EXCLUDE_URLS = [
    "/static/",
    "/admin/jsi18n/",
    "/favicon.ico",
]


class ExcludeCommonURLsFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()

        if message.startswith('"GET /'):  # Only check them all if it's a GET
            for url in EXCLUDE_URLS:
                if message.startswith(f'"GET {url}'):
                    return False

        return True
