import json
import unittest
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TypeVar
from uuid import UUID

from schema import Schema


class Level(Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"


@dataclass
class NoneSchema(Schema):
    foo: str = field(default=None)


@dataclass
class PersonSchema(Schema):
    name: str
    age: int
    hobby: list = field(default_factory=list)


@dataclass
class EmployeeSchema(Schema):
    person: PersonSchema
    uid: UUID
    office: str
    salary: Decimal
    level: Level
    registered: date


@dataclass
class SimpleSchema(Schema):
    created_at: datetime = field(default=None)
    buzz: str = field(default=None)


@dataclass
class TypeSchema(Schema):
    A: TypeVar


class TestSchemaLoad(unittest.TestCase):
    def test_load(self):
        data = {
            "person": {"name": "John Doe", "age": 30, "hobby": ["walk"]},
            "uid": "dc675e20-6e8b-4b05-a8ce-4459560526c3",
            "office": "main",
            "salary": 6500.1,
            "level": "middle",
            "registered": "2021-01-01",
        }
        instance = EmployeeSchema.load(data)

        self.assertIsInstance(instance, EmployeeSchema)
        self.assertIsInstance(instance.person, PersonSchema)
        self.assertIsInstance(instance.salary, Decimal)
        self.assertIsInstance(instance.level, Enum)
        self.assertIsInstance(instance.registered, date)

    def test_load_ignore_unknown(self):
        data = {
            "person": {"name": "John Doe", "age": 30, "hobby": ["walk"]},
            "uid": "dc675e20-6e8b-4b05-a8ce-4459560526c3",
            "office": "main",
            "salary": 6500.1,
            "level": "middle",
            "registered": "2021-01-01",
            "foo": "bar",
        }

        instance = EmployeeSchema.load(data)

        self.assertIsInstance(instance, EmployeeSchema)
        self.assertIsInstance(instance.person, PersonSchema)
        self.assertIsInstance(instance.salary, Decimal)
        self.assertIsInstance(instance.level, Enum)
        self.assertIsInstance(instance.registered, date)

    def test_load_date_iso_format(self):
        data = {
            "created_at": "2014-09-12T19:34:29Z",
            "buzz": "foo",
        }

        instance = SimpleSchema.load(data)

        self.assertIsInstance(instance, SimpleSchema)
        self.assertIsInstance(instance.created_at, datetime)
        self.assertIsInstance(instance.buzz, str)

    def test_load_without_field(self):
        data = {
            "foo": "bar",
        }
        instance = SimpleSchema.load(data)

        self.assertIsInstance(instance, SimpleSchema)
        self.assertEqual(instance.buzz, None)

    def test_load_invalid_type(self):
        expected = ("'name' must be of type str",)
        data = {
            "name": 123,
            "age": 30,
            "hobby": ["walk"],
        }

        with self.assertRaises(TypeError) as error:
            PersonSchema.load(data)

        self.assertEqual(error.exception.args, expected)

    def test_load_missing_required(self):
        with self.assertRaises(TypeError):
            PersonSchema.load({})

    def test_load_many(self):
        data = [
            {
                "person": {"name": "John Doe", "age": 30, "hobby": ["walk"]},
                "uid": "dc675e20-6e8b-4b05-a8ce-4459560526c3",
                "office": "main",
                "salary": 6500.1,
                "level": "middle",
                "registered": "2021-01-01",
                "foo": "bar",
            }
        ]
        instances = EmployeeSchema.load(data, many=True)

        self.assertIsInstance(instances, list)
        self.assertIsInstance(instances[0], EmployeeSchema)
        self.assertIsInstance(instances[0].person, PersonSchema)
        self.assertIsInstance(instances[0].salary, Decimal)
        self.assertIsInstance(instances[0].level, Enum)
        self.assertIsInstance(instances[0].registered, date)

    def test_loads(self):
        data = json.dumps(
            {
                "person": {"name": "John Doe", "age": 30, "hobby": ["walk"]},
                "uid": "dc675e20-6e8b-4b05-a8ce-4459560526c3",
                "office": "main",
                "salary": 6500.1,
                "level": "middle",
                "registered": "2021-01-01",
            }
        )
        instance = EmployeeSchema.loads(data)

        self.assertIsInstance(instance, EmployeeSchema)
        self.assertIsInstance(instance.person, PersonSchema)
        self.assertIsInstance(instance.salary, Decimal)
        self.assertIsInstance(instance.level, Enum)
        self.assertIsInstance(instance.registered, date)


class TestSchemaDump(unittest.TestCase):
    def test_dump(self):
        expected = {
            "person": {"name": "John Doe", "age": 30, "hobby": ["walk"]},
            "uid": "dc675e20-6e8b-4b05-a8ce-4459560526c3",
            "office": "main",
            "salary": 6500.1,
            "level": "middle",
            "registered": "2021-01-01",
        }
        instance = EmployeeSchema.load(expected)
        data = EmployeeSchema.dump(instance)

        self.assertDictEqual(data, expected)

    def test_dump_many(self):
        expected = [
            {
                "person": {"name": "John Doe", "age": 30, "hobby": ["walk"]},
                "uid": "dc675e20-6e8b-4b05-a8ce-4459560526c3",
                "office": "main",
                "salary": 6500.1,
                "level": "middle",
                "registered": "2021-01-01",
            }
        ]
        instances = EmployeeSchema.load(expected, many=True)
        data = EmployeeSchema.dump(instances, many=True)

        self.assertIsInstance(data, list)
        self.assertDictEqual(data[0], expected[0])

    def test_dumps(self):
        expected = {
            "person": {"name": "John Doe", "age": 30, "hobby": ["walk"]},
            "uid": "dc675e20-6e8b-4b05-a8ce-4459560526c3",
            "office": "main",
            "salary": 6500.1,
            "level": "middle",
            "registered": "2021-01-01",
        }
        instance = EmployeeSchema.load(expected)
        string = EmployeeSchema.dumps(instance)

        self.assertIsInstance(string, str)
        self.assertDictEqual(json.loads(string), expected)

    def test_dumps_not_serializable(self):
        expected = (("Object of type TypeVar is not JSON serializable"),)
        data = {
            "A": TypeVar("A"),
        }

        instance = TypeSchema.load(data)
        with self.assertRaises(TypeError) as error:
            TypeSchema.dumps(instance)

        self.assertEqual(error.exception.args, expected)


class TestSchema(unittest.TestCase):
    def test_none_attr(self):
        instance = NoneSchema()

        self.assertIsNone(instance.foo)

    def test_missing_required(self):
        with self.assertRaises(TypeError):
            PersonSchema()

    def test_invalid_type(self):
        expected = ("'age' must be of type int",)

        with self.assertRaises(TypeError) as error:
            PersonSchema("foo", "bar")

        self.assertEqual(error.exception.args, expected)
