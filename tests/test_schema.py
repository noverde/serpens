import unittest
from dataclasses import dataclass, field

from schema import Schema


@dataclass
class PersonSchema(Schema):
    name: str
    age: int
    hobby: list = field(default_factory=list)


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
