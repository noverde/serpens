import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from uuid import UUID


@dataclass
class Schema:
    def __post_init__(self):
        errors = []
        for field in fields(self):
            if field.default is None and getattr(self, field.name) is None:
                continue
            if not isinstance(getattr(self, field.name), field.type):
                msg = f"'{field.name}' must be of type {field.type.__name__}"
                errors.append(msg)
        if errors:
            raise TypeError(*errors)

    @classmethod
    def load(cls, dictionary, many=False):
        data_copy = deepcopy(dictionary)
        data = {}

        if isinstance(data_copy, dict):
            for key, value in data_copy.items():
                if key in cls.__dict__["__dataclass_fields__"]:
                    data[key] = value
        else:
            data = data_copy

        if many:
            return list(map(cls.load, data))

        for field in fields(cls):
            if field.name not in data or data[field.name] is None:
                continue  # pragma: no cover
            # cast special types
            if field.type in (date, datetime, time):
                if isinstance(data[field.name], str) and "Z" in data[field.name]:
                    data[field.name] = data[field.name].replace("Z", "")
                data[field.name] = field.type.fromisoformat(data[field.name])
            elif field.type in (Decimal, UUID):
                data[field.name] = field.type(data[field.name])
            elif issubclass(field.type, Enum):
                data[field.name] = field.type(data[field.name])
            elif is_dataclass(field.type):
                data[field.name] = field.type.load(data[field.name])

        try:
            instance = cls(**data)
        except TypeError as error:
            message = error.args[0] if error.args else ""
            pattern = (
                r"^(\w+\.)?__init__\(\) missing \d+ required positional "
                r"arguments?: ('\w+',?\s?(and\s?)?)+$"
            )

            if re.fullmatch(pattern, message):
                matchs = re.findall(r"('\w+')", message)
                missing = [f"{m} is a required field" for m in matchs]
                raise TypeError(*missing)

            raise error

        return instance

    @classmethod
    def loads(cls, json_string, many=False):
        data = json.loads(json_string)
        return list(map(cls.load, data)) if many else cls.load(data)

    @classmethod
    def dump(cls, instance, many=False, decoder=json.JSONDecoder):
        string = cls.dumps(instance, many)
        return json.loads(string, cls=decoder)

    @classmethod
    def dumps(cls, instance, many=False):
        data = list(map(asdict, instance)) if many else asdict(instance)
        return json.dumps(data, cls=SchemaEncoder)


class SchemaEncoder(json.JSONEncoder):
    def default(self, obj):
        # cast special types
        if isinstance(obj, (date, datetime, time)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        return super().default(obj)
