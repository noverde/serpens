from pony.orm import Database as PonyDatabase

from serpens import envvars


class Database(PonyDatabase):
    @staticmethod
    def _parse_uri(uri: str):
        if not uri:
            raise ValueError("uri must be not empty")

        try:
            urlparts = uri.split("://")
            if len(urlparts) < 2:
                raise

            provider = urlparts[0]
            if provider == "sqlite":
                uri = urlparts[1]
        except Exception:
            raise ValueError("uri must be a valid database URI")

        return provider, uri

    def __init__(self, uri=None):
        if uri is None:
            super().__init__()
        else:
            provider, uri = Database._parse_uri(uri)
            super().__init__(provider, uri)

    def bind(self, uri=None, mapping=False, check_tables=False):
        if uri is None:
            uri = envvars.get("DATABASE_URL")

        provider, uri = Database._parse_uri(uri)
        result = super().bind(provider, uri)

        if mapping:
            self.generate_mapping(check_tables=check_tables)

        return result
