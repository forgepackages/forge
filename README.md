# Forge

<img height="100" width="100" src="https://user-images.githubusercontent.com/649496/176748343-3829aad8-4bcf-4c25-bb5d-6dc1f796fac0.png" align="right" />

**Quickly build a professional web app using Django.**

Forge is a set of opinions for how to build with Django.
It guides how you work,
chooses what tools you use,
and makes decisions so you don't have to.

At it's core,
Forge *is* Django.
But we've taken a number of steps to make it even easier to build and deploy a production-ready app on day one.

If you're an experienced Django user,
you'll understand and (hopefully) agree with some of Forge's opinions.
If you're new to Django or building web applications,
we've simply removed questions that you might not even be aware of.

Forge will get you from *zero to one* on a revenue-generating SaaS, internal business application, or hobby project.

## Quickstart

Start a new project in 5 minutes:

```sh
curl -sSL https://forgepackages.com/quickstart.py | python3 - my-project
```

[![Forge Django quickstart](https://user-images.githubusercontent.com/649496/173145833-e4f96a4c-efb6-4cc3-b118-184be1a007f1.png)](https://www.youtube.com/watch?v=wYMRxTGDmdU)


### What's included

Things that come with Forge,
that you won't get from Django itself:

- Configure settings with environment variables
- A minimal `settings.py` with sane, opinionated defaults
- Extraneous files (`manage.py`, `wsgi.py`, `asgi.py`) have been removed unless you need to customize them
- Send emails using Django templates (ex. `templates/email/welcome.html`)
- Default form rendering with Tailwind classes
- Login in with email address (in addition to usernames)
- Abstract models for common uses (UUIDs, created_at, updated_at, etc.)
- Test using [pytest](https://docs.pytest.org/en/latest/) and [pytest-django](https://pytest-django.readthedocs.io/en/latest/)
- Default HTTP error templates (400, 403, 404, 500)
- Default Tailwind-styled password change and password reset templates
- Default Tailwind-styled login template
- Default Tailwind-styled sign up template
- Start with a custom user model (`users.User`)
- Start with a "team" model (`teams.Team`)

We're also able to make some decisions about what tools you use *with* Django -- things that Django (rightfully) doesn't take a stance on:

- Deploy using [Heroku](https://heroku.com/)
- Manage Python dependencies using [Poetry](https://python-poetry.org/)
- Style using [Tailwind CSS](https://tailwindcss.com/)
- Format your code using [black](https://github.com/psf/black) and [isort](https://github.com/PyCQA/isort)
- CI testing with GitHub Actions

All of this comes together with a `forge` CLI.


## Existing projects

A lot (but not all) of the Forge features can be integrated into existing projects by installing select packages:

- [forge-work](https://github.com/forgepackages/forge-work)
- [forge-tailwind](https://github.com/forgepackages/forge-tailwind)
- [forge-db](https://github.com/forgepackages/forge-db)
- [forge-heroku](https://github.com/forgepackages/forge-heroku)
- [forge-format](https://github.com/forgepackages/forge-format)

You can also look at the [Forge starter-template](https://github.com/forgepackages/starter-template),
which is what the quickstart uses to start a new project.


## Inspired by

- [create-react-app](https://create-react-app.dev/)
- [Bullet Train](https://bullettrain.co/)
- [SaaS Pegasus](https://www.saaspegasus.com/)
- [Laravel Spark](https://spark.laravel.com/)
