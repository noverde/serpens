import json
import unittest
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, TypeVar
from uuid import UUID

from schema import Schema


class Level(Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"


@dataclass
class NoneSchema(Schema):
    foo: str = None


@dataclass
class NoneSchemaOptional(Schema):
    foo: Optional[str] = None


@dataclass
class PersonSchema(Schema):
    name: str
    age: int
    hobby: list = field(default_factory=list)


@dataclass
class PersonSchemaOptional(Schema):
    name: Optional[str]
    age: Optional[int]
    hobby: Optional[list] = field(default_factory=list)


@dataclass
class EmployeeSchema(Schema):
    person: PersonSchema
    uid: UUID
    office: str
    salary: Decimal
    level: Level
    registered: date


@dataclass
class EmployeeSchemaOptional(Schema):
    person: Optional[PersonSchemaOptional]
    uid: Optional[UUID]
    office: Optional[str]
    salary: Optional[Decimal]
    level: Optional[Level]
    registered: Optional[date]


@dataclass
class SimpleSchema(Schema):
    created_at: datetime = None
    buzz: str = None


@dataclass
class SimpleSchemaOptional(Schema):
    created_at: Optional[datetime] = None
    buzz: Optional[str] = None


@dataclass
class TypeSchema(Schema):
    A: TypeVar


@dataclass
class TypeSchemaOptional(Schema):
    A: Optional[TypeVar]


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

        type_structures = [
            (EmployeeSchema, PersonSchema),
            (EmployeeSchemaOptional, PersonSchemaOptional),
        ]
        for type_structure in type_structures:
            with self.subTest(msg=type_structure[0].__name__):
                instance = type_structure[0].load(data)

                self.assertIsInstance(instance, type_structure[0])
                self.assertIsInstance(instance.person, type_structure[1])
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

        type_structures = [
            (EmployeeSchema, PersonSchema),
            (EmployeeSchemaOptional, PersonSchemaOptional),
        ]
        for type_structure in type_structures:
            with self.subTest(msg=type_structure[0].__name__):
                instance = type_structure[0].load(data)

                self.assertIsInstance(instance, type_structure[0])
                self.assertIsInstance(instance.person, type_structure[1])
                self.assertIsInstance(instance.salary, Decimal)
                self.assertIsInstance(instance.level, Enum)
                self.assertIsInstance(instance.registered, date)

    def test_load_date_iso_format(self):
        data = {
            "created_at": "2014-09-12T19:34:29Z",
            "buzz": "foo",
        }

        types = [SimpleSchema, SimpleSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                instance = type.load(data)

                self.assertIsInstance(instance, type)
                self.assertIsInstance(instance.created_at, datetime)
                self.assertIsInstance(instance.buzz, str)

    def test_load_without_field(self):
        data = {
            "foo": "bar",
        }

        types = [SimpleSchema, SimpleSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                instance = type.load(data)

                self.assertIsInstance(instance, type)
                self.assertEqual(instance.buzz, None)

    def test_load_invalid_type(self):
        expected = ("'name' must be of type str",)
        data = {
            "name": 123,
            "age": 30,
            "hobby": ["walk"],
        }

        types = [PersonSchema, PersonSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                with self.assertRaises(TypeError) as error:
                    type.load(data)

                self.assertEqual(error.exception.args, expected)

    def test_load_missing_required(self):
        expected = ("'name' is a required field", "'age' is a required field")

        types = [PersonSchema, PersonSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                with self.assertRaises(TypeError) as error:
                    type.load({})

                self.assertEqual(error.exception.args, expected)

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
        type_structures = [
            (EmployeeSchema, PersonSchema),
            (EmployeeSchemaOptional, PersonSchemaOptional),
        ]
        for type_structure in type_structures:
            with self.subTest(msg=type_structure[0].__name__):
                instances = type_structure[0].load(data, many=True)

                self.assertIsInstance(instances, list)
                self.assertIsInstance(instances[0], type_structure[0])
                self.assertIsInstance(instances[0].person, type_structure[1])
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
        type_structures = [
            (EmployeeSchema, PersonSchema),
            (EmployeeSchemaOptional, PersonSchemaOptional),
        ]
        for type_structure in type_structures:
            with self.subTest(msg=type_structure[0].__name__):
                instance = type_structure[0].loads(data)

                self.assertIsInstance(instance, type_structure[0])
                self.assertIsInstance(instance.person, type_structure[1])
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
        types = [EmployeeSchema, EmployeeSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                instance = type.load(expected)
                data = type.dump(instance)

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
        types = [EmployeeSchema, EmployeeSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                instances = type.load(expected, many=True)
                data = type.dump(instances, many=True)

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

        types = [EmployeeSchema, EmployeeSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                instance = type.load(expected)
                string = type.dumps(instance)

                self.assertIsInstance(string, str)
                self.assertDictEqual(json.loads(string), expected)

    def test_dumps_not_serializable(self):
        expected = (("Object of type TypeVar is not JSON serializable"),)
        data = {
            "A": TypeVar("A"),
        }

        types = [TypeSchema, TypeSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                instance = type.load(data)
                with self.assertRaises(TypeError) as error:
                    type.dumps(instance)

                self.assertEqual(error.exception.args, expected)


class TestSchema(unittest.TestCase):
    def test_none_attr(self):
        types = [NoneSchema, NoneSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                instance = type()

                self.assertIsNone(instance.foo)

    def test_missing_required(self):
        expected = (("__init__() missing 2 required positional " + "arguments: 'name' and 'age'"),)

        types = [PersonSchema, PersonSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                with self.assertRaises(TypeError) as error:
                    type()

                self.assertEqual(error.exception.args, expected)

    def test_invalid_type(self):
        expected = ("'age' must be of type int",)

        types = [PersonSchema, PersonSchemaOptional]
        for type in types:
            with self.subTest(msg=type.__name__):
                with self.assertRaises(TypeError) as error:
                    type("foo", "bar")

                self.assertEqual(error.exception.args, expected)
