import unittest
from dataclasses import dataclass
from decimal import Decimal

import boto3
from moto import mock_dynamodb

from serpens import document


@dataclass
class MyDocument(document.BaseDocument):
    _table_name_ = "my_document"

    id: str
    name: str
    average: Decimal


class TestBaseDocument(unittest.TestCase):
    m_dynamodb = mock_dynamodb()

    @classmethod
    def setUpClass(cls):
        cls.m_dynamodb.start()

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.create_table(
            TableName="my_document",
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )

        table.put_item(Item={"id": "2", "name": "Test2", "average": Decimal(15)})

    @classmethod
    def tearDownClass(cls):
        cls.m_dynamodb.stop()

    def test_save_item(self):
        my_document = MyDocument("1", "FooBar", Decimal(10.5))

        result = my_document.save()

        self.assertIsNotNone(result)

        my_document = MyDocument.get_by_key({"id": "1"})

        self.assertIsInstance(my_document, MyDocument)
        self.assertEqual(my_document.id, "1")
        self.assertEqual(my_document.name, "FooBar")
        self.assertEqual(my_document.average, Decimal(10.5))

    def test_get_item(self):
        my_document = MyDocument.get_by_key({"id": "2"})

        self.assertIsInstance(my_document, MyDocument)
        self.assertEqual(my_document.id, "2")
        self.assertEqual(my_document.name, "Test2")
        self.assertEqual(my_document.average, Decimal(15))

    def test_get_item_item_not_found(self):
        my_document = MyDocument.get_by_key({"id": "3"})

        self.assertIsNone(my_document)
