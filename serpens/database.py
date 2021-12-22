try:
    from pony.orm import Database

    PONY_NOT_FOUND = False
except ImportError:
    PONY_NOT_FOUND = True


def get_connection(database_url: str):
    urlparts = database_url.split("://")
    provider = urlparts[0]
    if provider == "sqlite":
        database_url = urlparts[1]

    return [provider, database_url]


def setup(database_url: str) -> Database:
    if PONY_NOT_FOUND:
        raise Exception("Couldn't setup database because PonyORM wasn't present in modules")

    tmp = database_url.split("://")
    drive = tmp[0]
    if drive == "sqlite":
        database_url = tmp[1]
    return Database(drive, database_url)
