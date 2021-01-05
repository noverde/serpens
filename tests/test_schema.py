import json
import unittest
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID

from schema import Schema


class Level(Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"


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


class TestSchema(unittest.TestCase):
    def test_missing_required(self):
        expected = (
            (
                "__init__() missing 2 required positional "
                + "arguments: 'name' and 'age'"
            ),
        )

        with self.assertRaises(TypeError) as error:
            PersonSchema()

        self.assertEqual(error.exception.args, expected)

    def test_invalid_type(self):
        expected = ("'age' must be of type int",)

        with self.assertRaises(TypeError) as error:
            PersonSchema("foo", "bar")

        self.assertEqual(error.exception.args, expected)

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

    def test_load_many(self):
        data = [
            {
                "person": {"name": "John Doe", "age": 30, "hobby": ["walk"]},
                "uid": "dc675e20-6e8b-4b05-a8ce-4459560526c3",
                "office": "main",
                "salary": 6500.1,
                "level": "middle",
                "registered": "2021-01-01",
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
