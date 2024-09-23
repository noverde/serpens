import os
import shlex
import subprocess
import time
import unittest

# start and stop run functions so we can call it later
default_start_test_run = unittest.result.TestResult.startTestRun
default_stop_test_run = unittest.result.TestResult.stopTestRun

database = None
schema = None
testgres_startup_delay = int(os.getenv("TESTGRES_STARTUP_DELAY", 1))


def docker_shell(cmd, output=True):
    result = subprocess.run(shlex.split(cmd), capture_output=True, encoding="utf-8")
    if output and result.stderr:
        print(result.stderr)
    return result


def docker_start():
    imgname = "postgres:13"
    cmdargs = "-d --rm --name testgres"
    envvars = "-e POSTGRES_USER=testgres -e POSTGRES_PASSWORD=testgres"
    publish = "-p 5432"
    return docker_shell(f"docker run {cmdargs} {publish} {envvars} {imgname}")


def docker_stop():
    return docker_shell("docker stop testgres", output=False)


def docker_pg_isready():
    return docker_shell("docker exec testgres pg_isready").returncode


def docker_pg_user_path():
    if schema is None:
        return None

    create_schema = " ".join([f"CREATE SCHEMA IF NOT EXISTS {s};" for s in schema.split(",")])
    set_search_path = f"ALTER USER testgres SET search_path = {schema}"
    cmd = f"psql -U testgres -d testgres -c '{create_schema}' -c '{set_search_path}'"

    return docker_shell(f"docker exec testgres {cmd}", output=False).returncode


def docker_port():
    stdout = docker_shell("docker port testgres").stdout
    result = stdout.split("\n")[0]
    return result.split(":")[1]


def docker_init():
    print("Docker engine initialization...")

    docker_stop()
    docker_start()

    while docker_pg_isready():
        time.sleep(testgres_startup_delay)

    docker_pg_user_path()
    port = docker_port()

    return f"postgres://testgres:testgres@localhost:{port}/testgres"


def start_test_run(self):
    try:
        uri = docker_init()

        database.bind(uri, mapping=True)
        database.create_tables()

        default_start_test_run(self)
    except Exception as e:
        print(str(e))


def stop_test_run(self):
    docker_stop()
    default_stop_test_run(self)


def setup(db, uri=None, default_schema=None):
    if uri is None:
        uri = os.environ.get("DATABASE_URL")

    if uri:
        return db.create_tables()

    global database, schema
    database = db
    schema = default_schema
    unittest.result.TestResult.startTestRun = start_test_run
    unittest.result.TestResult.stopTestRun = stop_test_run
