# Customizing templates

To customize templates, copy these into your own app and modify them from there.

You do not need to customize/duplicate forge_base.html at all.
If you find yourself wanting to make significant changes to it,
you should instead create your own base.html that doesn't `{% extends "forge_base.html" %}`.
The only requirement for base.html is that you have `{% block content %}` and `{% block html_title %}` in order for the other default templates to work.
