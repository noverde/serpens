try:
    from yoyo import read_migrations
    from yoyo import get_backend
    YOYO_NOT_FOUND = False
except ImportError:
    YOYO_NOT_FOUND = True

try:
    from pony.orm import Database
    PONY_NOT_FOUND = False
except ImportError:
    PONY_NOT_FOUND = True


def migrate(database_url, migrations_path="./migrations"):
    if YOYO_NOT_FOUND:
        raise Exception(
            "Couldn't run migrations because yoyo wasn't present in modules")

    backend = get_backend(database_url)
    migrations = read_migrations(migrations_path)
    backend.apply_migrations(backend.to_apply(migrations))


def setup(database_url: str) -> Database:
    if PONY_NOT_FOUND:
        raise Exception(
            "Couldn't setup database because PonyORM wasn't present in modules")

    tmp = database_url.split("://")
    drive = tmp[0]
    if drive == "sqlite":
        database_url = tmp[1]
    return Database(drive, database_url)


def make_response(data, prefix=None, include_relationship=False):
    if isinstance(data, list):
        response = list(map(lambda x: x.to_dict(related_objects=include_relationship, with_collections=include_relationship), data))
    else:
        response = data.to_dict(related_objects=include_relationship, with_collections=include_relationship)
    
    return { prefix : response } if prefix else response