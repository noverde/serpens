from dataclasses import dataclass, fields


@dataclass
class Schema:
    def __post_init__(self):
        errors = []
        for field in fields(self):
            if not isinstance(getattr(self, field.name), field.type):
                msg = f"'{field.name}' must be of type {field.type.__name__}"
                errors.append(msg)
        if errors:
            raise TypeError(*errors)
