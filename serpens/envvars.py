import os
import shlex

from serpens import parameters, secrets_manager


def get(key, default=None):
    result = os.getenv(key, default)

    if result is None:
        return None

    if result.startswith("parameters://"):
        tmp = result.split("://")[1]
        return parameters.get(tmp)

    if result.startswith("secrets://"):
        tmp = result.split("://")[1].split("?")
        secret_name = tmp[0]
        secret_key = tmp[1] if len(tmp) > 1 else None
        return secrets_manager.get(secret_name, secret_key)

    return result


def load_dotenv(filename=".env") -> None:
    if not os.path.isfile(filename):
        return

    try:
        stream = open(filename, "r")
        buffer = stream.readlines()
        stream.close()
    except Exception:
        return

    for line in buffer:
        tokens = list(shlex.shlex(line, posix=True, punctuation_chars="="))
        if len(tokens) < 2:
            continue
        if tokens[0] == "export" and tokens[2] == "=":
            tokens.pop(0)

        os.environ[tokens[0]] = tokens[2] if len(tokens) > 2 else ""


load_dotenv()
