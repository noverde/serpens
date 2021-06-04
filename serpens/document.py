import json
from dataclasses import dataclass
from decimal import Decimal

import boto3

from serpens.schema import Schema


class DynamoDBDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(parse_float=Decimal, *args, **kwargs)


@dataclass
class BaseDocument(Schema):
    def __post_init__(self):
        super().__post_init__()

        self._table_ = self.get_table()

    @classmethod
    def get_table(cls):
        dynamodb = boto3.resource("dynamodb")
        table_name = getattr(cls, "_table_name_", None)

        return dynamodb.Table(table_name)

    @classmethod
    def get_by_key(cls, key):
        table = cls.get_table()
        response = table.get_item(Key=key)

        if "Item" not in response:
            return None

        return cls.load(response["Item"])

    def save(self):
        data = self.dump(self, decoder=DynamoDBDecoder)
        response = self._table_.put_item(Item=data)

        return response
