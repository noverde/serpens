import logging

from yoyo import read_migrations
from yoyo import get_backend

from serpens import envvars


def migrate(uri, migrations_path):
    backend = get_backend(uri)
    migrations = read_migrations(migrations_path)
    backend.apply_migrations(backend.to_apply(migrations))


def migrate_handler(event, context):
    uri = envvars.get("DATABASE_URL")
    path = envvars.get("DATABASE_MIGRATIONS_PATH", "./")

    logging.info("Migrating database...")
    migrate(uri, path)
    logging.info("Migration successful")
