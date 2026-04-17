import os
import shlex
import subprocess
import time
import unittest
import uuid

from serpens import database

# start and stop run functions so we can call it later
default_start_test_run = unittest.result.TestResult.startTestRun
default_stop_test_run = unittest.result.TestResult.stopTestRun

base = None
schema = None
testgres_startup_delay = int(os.getenv("TESTGRES_STARTUP_DELAY", 1))
testgres_startup_timeout = int(os.getenv("TESTGRES_STARTUP_TIMEOUT", 30))
container_name = f"testgres_{uuid.uuid4().hex}"


def docker_shell(cmd, output=True):
    result = subprocess.run(shlex.split(cmd), capture_output=True, encoding="utf-8")
    if output and result.stderr:
        print(result.stderr)
    return result


def docker_start():
    imgname = "postgres:13"
    cmdargs = f"-d --rm --name {container_name}"
    envvars = "-e POSTGRES_USER=testgres -e POSTGRES_PASSWORD=testgres"
    publish = "-p 5432"
    return docker_shell(f"docker run {cmdargs} {publish} {envvars} {imgname}")


def docker_stop():
    return docker_shell(f"docker stop {container_name}", output=False)


def docker_pg_isready():
    return docker_shell(f"docker exec {container_name} pg_isready").returncode


def docker_pg_user_path():
    if schema is None:
        return None

    create_schema = " ".join([f"CREATE SCHEMA IF NOT EXISTS {s};" for s in schema.split(",")])
    set_search_path = f"ALTER USER testgres SET search_path = {schema}"
    cmd = f"psql -U testgres -d testgres -c '{create_schema}' -c '{set_search_path}'"

    return docker_shell(f"docker exec {container_name} {cmd}", output=False).returncode


def docker_port():
    stdout = docker_shell(f"docker port {container_name}").stdout
    result = stdout.split("\n")[0]
    return result.split(":")[1]


def docker_init():
    print("Docker engine initialization...")

    docker_stop()
    docker_start()

    deadline = time.monotonic() + testgres_startup_timeout
    while docker_pg_isready():
        if time.monotonic() > deadline:
            raise RuntimeError(f"postgres did not become ready within {testgres_startup_timeout}s")
        time.sleep(testgres_startup_delay)

    docker_pg_user_path()
    port = docker_port()

    return f"postgresql+psycopg2://testgres:testgres@localhost:{port}/testgres"


def start_test_run(self):
    try:
        uri = docker_init()
        engine = database.bind(uri)
        base.metadata.create_all(engine)
        default_start_test_run(self)
    except Exception as e:
        print(str(e))


def stop_test_run(self):
    try:
        database.dispose()
    finally:
        docker_stop()
        default_stop_test_run(self)


def setup(declarative_base, uri=None, default_schema=None):
    if uri is None:
        uri = os.environ.get("DATABASE_URL")

    if uri:
        engine = database.bind(uri)
        declarative_base.metadata.create_all(engine)
        return

    global base, schema
    base = declarative_base
    schema = default_schema
    unittest.result.TestResult.startTestRun = start_test_run
    unittest.result.TestResult.stopTestRun = stop_test_run
