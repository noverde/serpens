from yoyo import read_migrations
from yoyo import get_backend
from pony.orm import Database



def migrate(database_url, migrations_path="./migrations"):
    backend = get_backend(database_url)
    migrations = read_migrations(migrations_path)
    backend.apply_migrations(backend.to_apply(migrations))


def setup(database_url: str) -> Database:
    tmp = database_url.split("://")
    drive = tmp[0]
    if drive == "sqlite":
        database_url = tmp[1]
    return Database(drive, database_url)
