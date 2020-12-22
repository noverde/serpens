from pony.orm.core import db_session

from serpens import database


def test_migrate():
    database_url = "sqlite:///serpens/test.db"
    path = "./tests/samples/migrations"
    database.migrate(database_url, path)

@db_session
def test_database():
    db = database.setup("sqlite://test.db")
    db.execute("INSERT INTO foo (id, bar) VALUES (1, 'test')")
    result = db.get("SELECT * FROM foo WHERE id = 1")
    print(result)
    assert result is not None
