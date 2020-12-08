import os

from serpens import database
from sqlalchemy.orm import mapper
from sqlalchemy import (
    Table,
    MetaData,
    Column,
    Integer
)


class TestModel:
    id: int



def test_database():
    database.setup("sqlite:///:memory:")
    database.Engine.execute("CREATE TABLE test (id INTEGER)")
    database.Engine.execute("INSERT INTO test (id) VALUES (1)")
    result_set = database.Engine.execute("SELECT * FROM test").fetchall()
    assert len(result_set) == 1


def test_session():
    database.setup("sqlite:///:memory:")
    print(database.Engine)
    print(database.Session)

    metadata = MetaData()
    test_table = Table("test", metadata, Column('id', Integer, primary_key=True))
    metadata.create_all(database.Engine)
    mapper(TestModel, test_table)

    session = database.Session()
    
    test_item = TestModel()
    test_item.id = 1
    session.add(test_item)
    
    assert session.query(TestModel).get(1).id == 1