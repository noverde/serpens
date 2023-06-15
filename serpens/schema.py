import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Union
from uuid import UUID


class SchemaUnsupportedTypeException(Exception):
    pass


@dataclass
class Schema:
    def __post_init__(self):
        errors = []
        for field in fields(self):
            if field.default is None and getattr(self, field.name) is None:
                continue

            field_type = self._get_raw_type(field.type)

            if not isinstance(getattr(self, field.name), field_type):
                msg = f"'{field.name}' must be of type {field_type.__name__}"
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
            field_type = cls._get_raw_type(field.type)

            if field_type in (date, datetime, time):
                if isinstance(data[field.name], str) and "Z" in data[field.name]:
                    data[field.name] = data[field.name].replace("Z", "")

                data[field.name] = field_type.fromisoformat(data[field.name])
            elif field_type in (Decimal, UUID):
                data[field.name] = field_type(data[field.name])
            elif issubclass(field_type, Enum):
                data[field.name] = field_type(data[field.name])
            elif is_dataclass(field_type):
                data[field.name] = field_type.load(data[field.name])

        try:
            instance = cls(**data)
        except TypeError as error:
            message = error.args[0] if error.args else ""
            pattern = (
                r"^__init__\(\) missing \d+ required positional "
                r"arguments?: ('\w+',?\s?(and\s?)?)+$"
            )

            if re.fullmatch(pattern, message):
                matchs = re.findall(r"('\w+')", message)
                missing = [f"{m} is a required field" for m in matchs]
                raise TypeError(*missing)

            raise error

        return instance

    @classmethod
    def _get_raw_type(cls, field_type):
        if not hasattr(field_type, "__origin__") or field_type.__origin__ is not Union:
            return field_type

        args = field_type.__args__

        none_class = type(None)
        raw_type = None
        has_none = False
        for arg in args:
            if arg == none_class:
                has_none = True
            else:
                raw_type = arg

        if len(args) != 2 or not has_none or arg is None:
            error_msg = (
                f"Unsupported {str(field_type)}. This Union is not equivalent to an Optional."
            )
            raise SchemaUnsupportedTypeException(error_msg)

        return raw_type

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
