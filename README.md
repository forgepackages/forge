# Forge

**Quickly build a professional web app using Django.**

Forge is a set of opinions.
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
$ curl -sSL https://djangoforge.dev/quickstart.py | python3
```

## What's included

Things that come with Forge,
that you won't get from Django itself:

- Most settings are determined by environment variables
- Most settings have updated defaults, and you don't need to know about most of them
- Extraneous files (`manage.py`, `wsgi.py`, `asgi.py`) have been removed unless you need to customize them
- You start with a custom user model (`users.User`)
- You start with a "team" model (`teams.Team`)
- template email
- base template
- form templates
- email login
- abstract models
- db commands
- Test using [pytest](https://docs.pytest.org/en/latest/) and [pytest-django](https://pytest-django.readthedocs.io/en/latest/)
- Static files served with [WhiteNoise](http://whitenoise.evans.io/en/stable/)

We're also able to make some decisions about what tools you use *with* Django -- things that Django (rightfully) doesn't take a stance on:

- Deploy using [Heroku](https://heroku.com/)
- Manage Python dependencies using [Poetry](https://python-poetry.org/)
- Style using [Tailwind CSS](https://tailwindcss.com/)
- Format your code using [black](https://github.com/psf/black) and [isort](https://github.com/PyCQA/isort)

Lastly, we bring it all together with a `forge` CLI:

### Local development

- `forge work` - your local development command
- `forge test` - run tests using pytest
- `forge format` - format app code with black and isort
- `forge pre-commit`
- `forge django` - passes commands to Django manage.py (i.e. `forge manage makemigrations`)

### Deployment

- `forge pre-deploy`
- `forge serve` - a production

### Misc.

- `forge init` - used by the quickstart, but can be used by itself too
