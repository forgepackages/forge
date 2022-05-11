from django.core.checks import Error, Tags, register
from django.db import connection


@register("forge", Tags.database)
def check_database_tables(app_configs, **kwargs):
    databases = kwargs.get("databases", None)
    if not databases:
        return []

    errors = []

    for database in databases:
        db_tables = connection.introspection.table_names()
        model_tables = connection.introspection.django_table_names()

        unknown_tables = set(db_tables) - set(model_tables)
        unknown_tables.discard("django_migrations")  # Know this could be there
        if unknown_tables:
            table_names = ", ".join(unknown_tables)
            specific_hint = f'echo "DROP TABLE IF EXISTS {unknown_tables.pop()}" | forge django dbshell'
            errors.append(
                Error(
                    f"Unknown tables in {database} database: {table_names}",
                    hint=f"Tables may be from apps/models that have been uninstalled. Make sure you have a backup and delete the tables manually (ex. `{specific_hint}`).",
                    id="forge.db.E001",
                )
            )

    return errors
