import os

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
