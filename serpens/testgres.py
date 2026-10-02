import os
import shlex
import socket
import subprocess
import sys
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
postgres_image = os.getenv("TESTGRES_IMAGE", "postgres:13")
postgres_base_port = int(os.getenv("TESTGRES_PORT", 5433))
redis_base_port = int(os.getenv("TESTGRES_REDIS_PORT", 6380))

# "host" runs the containers with --network=host on a fixed port (base + runner slot)
# instead of publishing a Docker-assigned port. Docker's published-port NAT breaks while a
# VPN is up on Linux (connects fail with "server closed the connection unexpectedly"), so
# host is the default there. Docker Desktop (macOS/Windows) doesn't expose host networking
# to the host, so it keeps the classic "bridge" publishing.
network_mode = os.getenv("TESTGRES_NETWORK") or (
    "host" if sys.platform.startswith("linux") else "bridge"
)

PORT_LABEL = "serpens.testgres.port"
MAX_SLOT = 10000


def docker_shell(cmd, output=True):
    result = subprocess.run(shlex.split(cmd), capture_output=True, encoding="utf-8")
    if output and result.stderr:
        print(result.stderr)
    return result


def runner_slot(env=None):
    """Numeric slot taken from the digits of RUNNER_NAME ("runner-3" -> 3), 0 when unset.

    In host network mode each slot gets its own host port, so CI runners sharing a Docker
    host, and parallel workers started with `worker_env`, don't collide.
    """
    runner = (os.environ if env is None else env).get("RUNNER_NAME", "")
    digits = "".join(ch for ch in runner if ch.isdigit())
    return int(digits or "0") % MAX_SLOT


def worker_env(index, env=None):
    """Environment for parallel test worker `index`.

    Nests the worker under the current RUNNER_NAME slot (slot * 100 + index), so each
    worker of each runner gets its own Postgres/Redis host port. Pass the result as
    `env=` to the subprocess running that worker's `python -m unittest`.
    """
    env = dict(os.environ if env is None else env)
    env["RUNNER_NAME"] = str(runner_slot(env) * 100 + index)
    return env


def host_network():
    return network_mode == "host"


def postgres_port():
    return postgres_base_port + runner_slot()


def redis_port():
    return redis_base_port + runner_slot()


def _port_in_use(port):
    try:
        with socket.create_connection(("localhost", port), timeout=0.5):
            return True
    except OSError:
        return False


def _claim_host_port(port):
    """Free `port` for a new container, or fail fast with an actionable error.

    Containers left behind by a killed run carry our port label and are removed. Anything
    else listening on the port is not ours to stop.
    """
    stale = docker_shell(
        f"docker ps -aq --filter label={PORT_LABEL}={port}", output=False
    ).stdout.split()
    for container in stale:
        docker_shell(f"docker rm -f {container}", output=False)

    if _port_in_use(port):
        raise RuntimeError(
            f"testgres: port {port} is already in use; set TESTGRES_PORT/TESTGRES_REDIS_PORT "
            f"or RUNNER_NAME to pick another, or TESTGRES_NETWORK=bridge to publish a "
            f"Docker-assigned port instead"
        )


def docker_start():
    cmdargs = f"-d --rm --name {container_name}"
    envvars = "-e POSTGRES_USER=testgres -e POSTGRES_PASSWORD=testgres"
    if host_network():
        port = postgres_port()
        _claim_host_port(port)
        # PGPORT moves the server and is inherited by `docker exec` (pg_isready, psql).
        cmdargs += f" --label {PORT_LABEL}={port}"
        publish = f"--network=host -e PGPORT={port}"
    else:
        publish = "-p 5432"
    return docker_shell(f"docker run {cmdargs} {publish} {envvars} {postgres_image}")


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
    if host_network():
        return str(postgres_port())
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
    cmdargs = f"-d --rm --name {redis_container_name}"
    if host_network():
        port = redis_port()
        _claim_host_port(port)
        cmdargs += f" --label {PORT_LABEL}={port} --network=host"
        return docker_shell(f"docker run {cmdargs} {redis_image} redis-server --port {port}")
    return docker_shell(f"docker run {cmdargs} -p 6379 {redis_image}")


def docker_redis_stop():
    return docker_shell(f"docker stop {redis_container_name}", output=False)


def docker_redis_port():
    if host_network():
        return str(redis_port())
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
