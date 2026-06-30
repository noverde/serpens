import os
import shlex
import subprocess
import time
import unittest
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from serpens import database

default_start_test_run = unittest.result.TestResult.startTestRun
default_stop_test_run = unittest.result.TestResult.stopTestRun

base = None
schema = None
async_enabled = False
redis_enabled = False
external_uri = None
external_redis_url = None
testgres_startup_delay = int(os.getenv("TESTGRES_STARTUP_DELAY", 1))
testgres_startup_timeout = int(os.getenv("TESTGRES_STARTUP_TIMEOUT", 30))
container_name = f"testgres_{uuid.uuid4().hex}"
redis_container_name = f"testredis_{uuid.uuid4().hex}"
redis_image = os.getenv("TESTGRES_REDIS_IMAGE", "redis:7-alpine")
testgres_network = os.getenv("TESTGRES_DOCKER_NETWORK", "")
testgres_port = os.getenv("TESTGRES_PORT", "5433" if testgres_network else "5432")


def docker_shell(cmd, output=True):
    result = subprocess.run(shlex.split(cmd), capture_output=True, encoding="utf-8")
    if output and result.stderr:
        print(result.stderr)
    return result


def docker_start():
    imgname = "postgres:13"
    cmdargs = f"-d --rm --name {container_name}"
    envvars = "-e POSTGRES_USER=testgres -e POSTGRES_PASSWORD=testgres"
    if testgres_network:
        netargs = f"--network {testgres_network} -e PGPORT={testgres_port}"
        return docker_shell(f"docker run {cmdargs} {netargs} {envvars} {imgname}")
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
    if testgres_network:
        return testgres_port
    stdout = docker_shell(f"docker port {container_name}").stdout
    result = stdout.split("\n")[0]
    return result.split(":")[1]


def _wait_for_tcp(port, deadline):
    import socket

    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", int(port)), timeout=1):
                return True
        except OSError:
            time.sleep(testgres_startup_delay)
    return False


def _wait_for_postgres_accept(uri, deadline):
    import psycopg2

    last_err = None
    while time.monotonic() < deadline:
        try:
            conn = psycopg2.connect(uri.replace("postgresql+psycopg2", "postgresql"))
            conn.close()
            return True
        except psycopg2.OperationalError as e:
            last_err = e
            time.sleep(testgres_startup_delay)
    raise RuntimeError(f"postgres did not accept connections: {last_err}")


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

    if not _wait_for_tcp(port, deadline):
        raise RuntimeError(f"postgres TCP {port} did not open within {testgres_startup_timeout}s")

    uri = f"postgresql+psycopg2://testgres:testgres@localhost:{port}/testgres"
    _wait_for_postgres_accept(uri, deadline)
    return uri


def _bind_async_engine():
    sync_url = database._engine.url.render_as_string(hide_password=False)
    async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    database._async_engine = create_async_engine(async_url, poolclass=NullPool)
    database.AsyncSessionLocal = async_sessionmaker(
        bind=database._async_engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )


def docker_redis_start():
    cmdargs = f"-d --rm --name {redis_container_name} -p 6379"
    return docker_shell(f"docker run {cmdargs} {redis_image}")


def docker_redis_stop():
    return docker_shell(f"docker stop {redis_container_name}", output=False)


def docker_redis_port():
    stdout = docker_shell(f"docker port {redis_container_name}").stdout
    return stdout.split("\n")[0].split(":")[1]


def docker_redis_init():
    print("Docker redis initialization...")

    docker_redis_stop()
    docker_redis_start()

    deadline = time.monotonic() + testgres_startup_timeout
    port = docker_redis_port()
    if not _wait_for_tcp(port, deadline):
        raise RuntimeError(f"redis TCP {port} did not open within {testgres_startup_timeout}s")
    return f"redis://localhost:{port}"


def start_test_run(self):
    uri = external_uri or docker_init()
    engine = database.bind(uri)
    base.metadata.create_all(engine)
    if async_enabled:
        _bind_async_engine()
    if redis_enabled and not external_redis_url:
        os.environ["REDIS_URL"] = docker_redis_init()
    default_start_test_run(self)


def stop_test_run(self):
    try:
        database.dispose()
    finally:
        if not external_uri:
            docker_stop()
        if redis_enabled and not external_redis_url:
            docker_redis_stop()
        default_stop_test_run(self)


def setup(
    declarative_base,
    uri=None,
    default_schema=None,
    async_mode=False,
    redis_mode=False,
):
    """Wire up testgres for an app's test suite.

    `redis_mode=True` spins a Redis container alongside Postgres and sets the
    `REDIS_URL` env var, removing the per-app boilerplate (`pix-automatic`,
    `integrator-vcom`). If `REDIS_URL` is already set, the existing instance
    is reused.
    """
    global base, schema, async_enabled, redis_enabled, external_uri, external_redis_url
    async_enabled = async_mode
    redis_enabled = redis_mode
    base = declarative_base
    schema = default_schema
    external_uri = uri or os.environ.get("DATABASE_URL")
    external_redis_url = os.environ.get("REDIS_URL") if redis_mode else None
    unittest.result.TestResult.startTestRun = start_test_run
    unittest.result.TestResult.stopTestRun = stop_test_run
