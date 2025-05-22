import re
from typing import List, Tuple
from uuid import UUID


def validate_cpf(cpf: str) -> bool:
    if not cpf.isdigit() or len(cpf) != 11 or len(set(cpf)) == 1:
        return False

    def _validate_digit(numbers: List[int], index: int) -> bool:
        values = zip(numbers[0:index], range(index + 1, 1, -1))
        sum_of_products = sum(a * b for a, b in values)
        expected = (sum_of_products * 10 % 11) % 10
        return numbers[index] == expected

    numbers = tuple(map(int, cpf))
    ninth = _validate_digit(numbers, 9)
    tenth = _validate_digit(numbers, 10)

    return ninth and tenth


def validate_cnpj(cnpj: str) -> bool:
    if not cnpj.isdigit() or len(cnpj) != 14 or cnpj == cnpj[::-1]:
        return False

    def _digit(multiplicands: Tuple[int], multipliers: Tuple[int]) -> int:
        result = sum(a * b for a, b in zip(multiplicands, multipliers))
        remainder = result % 11
        digit = 0 if remainder < 2 else 11 - remainder
        return digit

    numbers = tuple(map(int, cnpj))

    multiplicands1 = numbers[:-2]
    multipliers1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    digit1 = _digit(multiplicands1, multipliers1)

    multiplicands2 = numbers[:-2] + (digit1,)
    multipliers2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    digit2 = _digit(multiplicands2, multipliers2)

    return numbers[-2:] == (digit1, digit2)


def validate_email(email: str) -> bool:
    if "@" not in email:
        return False

    user, domain = email.rsplit("@", 1)

    user_pattern = (
        r"(^[-!#$%&'+/=?^_`{}|~0-9a-z]+(\.[-!#$%&'+/=?^_`{}|~0-9a-z]+)*\Z"
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]'
        r'|\\[\001-\011\013\014\016-\177])*"\Z)'
    )

    if not re.match(user_pattern, user, flags=re.I | re.U):
        return False

    if domain == "localhost":
        return True

    domain_pattern = (
        r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
        r"(?:[A-Z]{2,6}|[A-Z0-9-]{2,})\Z"
        r"|^\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)"
        r"(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]\Z"
    )

    if not re.match(domain_pattern, domain, flags=re.I | re.U):
        return False

    return True


def validate_mobile_number(number: str) -> bool:
    match = re.match(r"^(?!(.)\1{10})[1-9]{2}9\d{8}$", number)
    return match is not None


def validate_pix(value: str) -> bool:
    if validate_cpf(value):
        return True

    if validate_cnpj(value):
        return True

    if validate_email(value):
        return True

    if validate_mobile_number(value.replace("+55", "")):
        return True

    try:
        UUID(value)
    except ValueError:
        pass
    else:
        return True

    return False


def validate_name(name: str) -> bool:
    match = re.match(r"^[^\d\W]{1}[\w.'\- ]{0,79}$", name)
    return match is not None
