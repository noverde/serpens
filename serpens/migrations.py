import logging

from yoyo import read_migrations
from yoyo import get_backend

from serpens import envvars


def migrate(uri=None, migrations_path=None):
    if uri is None:
        uri = envvars.get("DATABASE_URL")

    if migrations_path is None:
        migrations_path = envvars.get("DATABASE_MIGRATIONS_PATH", "./migrations")

    backend = get_backend(uri)
    migrations = read_migrations(migrations_path)
    backend.apply_migrations(backend.to_apply(migrations))


def migrate_handler(event, context):
    logging.info("Migrating database...")
    migrate()
    logging.info("Migration successful")
