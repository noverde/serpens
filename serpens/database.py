import os

import alembic.config
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


def _get_engine(database_url: str):
    if not database_url: 
        raise ValueError("Couldn't initialize database because env variable DATABASE_URL wasn't setted")

    debug_mode = bool(os.getenv("SQL_DEBUG_MODE", False))
    return create_engine(database_url, echo=debug_mode)


def setup(database_url: str):
    global Engine, Session
    Engine = _get_engine(database_url)
    Session = scoped_session(sessionmaker(bind=Engine, autoflush=True))


def migrate():
    alembicArgs = [
        "--raiseerr",
        "upgrade",
        "head",
    ]
    alembic.config.main(argv=alembicArgs)
    

class BaseModel:
    def save(self):
        session = Session()
        if not self.id:  # type: ignore
            session.add(self)
        else:
            self = session.merge(self)
        session.commit()
        session.refresh(self)
        session.close()
