class HTMLTitleMixin:
    html_title = ""
    html_title_prefix = ""
    html_title_suffix = ""

    def get_html_title(self):
        """Return the class title attr by default, but can customize this by overriding"""
        return self.html_title

    def get_html_title_prefix(self):
        return self.html_title_prefix

    def get_html_title_suffix(self):
        return self.html_title_suffix

    def generate_html_title(self):
        return (
            self.get_html_title_prefix()
            + self.get_html_title()
            + self.get_html_title_suffix()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["html_title"] = self.generate_html_title()
        return context
