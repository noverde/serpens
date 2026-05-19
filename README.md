# serpens

Shared Python building blocks for DotzInc services: thin layers over SQLAlchemy
2.0, Redis, httpx, Pub/Sub, SQS and friends. The lib stays out of the way —
apps import the underlying SDKs directly for the heavy lifting and use serpens
for the configuration that should not be duplicated across 24 repos.

- [SQS](#sqs) · [Lambda API](#lambda-api) · [Schema](#schema) · [CSV](#csv)
- [Database](#database) · [Migrations](#migrations) · [Pony → SQLAlchemy](#migrating-from-pony-orm)
- [DynamoDB](#dynamodb) · [Async HTTP](#async-http-client) · [Rate limiter](#rate-limiter)
- [Cache](#cache) · [Async Pub/Sub](#async-pub-sub-publisher) · [Test infra](#test-infrastructure-testgres)

## SQS

```python
from serpens import sqs

@sqs.handler
def message_processor(record: sqs.Record):
    print(record.body)
```

`sqs.Record` exposes `data`, `body`, `message_attributes`, `queue_name`, `sent_datetime`.

## Lambda API

```python
from serpens import api

@api.handler
def lambda_handler(request: api.Request):
    print(request.body)
```

`api.Request` exposes `authorizer`, `body`, `path`, `query`, `headers`, `identity`.
All but `body` are `AttrDict` — `request.path.user_id` shortcut for `request.path["user_id"]`.

### Async handlers (`api.async_handler`)

Same contract as `@api.handler`, but for `async def` handlers — needed when
the body awaits coroutines (FastAPI/Mangum integration, async DB sessions,
async HTTP clients).

```python
from serpens import api
from serpens.database import async_db_session

@api.async_handler
async def lambda_handler(request: api.Request):
    async with async_db_session() as sess:
        ...
```

**Why use it**

- **Single response/error contract.** `_build_response` and `_error_response`
  are shared with the sync version: same response shape, same elastic-apm
  capture, same JSON encoding via `SchemaEncoder`. No drift between sync
  and async handler responses across services.
- **Required to use async SQLAlchemy / `httpx` / `cache_async` inside a
  Lambda.** A regular `@api.handler` cannot `await`.

**Migration scenarios**

| Today's code | Move to | What you gain |
|---|---|---|
| `@api.handler def lambda_handler(...)` that calls `asyncio.run(...)` internally | `@api.async_handler async def lambda_handler(...)` | One event loop per invocation, no `asyncio.run` boilerplate, can use async libs throughout the handler |
| FastAPI / Mangum bridge with hand-rolled response shaping | `@api.async_handler` | Same response shape across sync/async Lambdas, central elastic-apm capture |

The sync `@api.handler` (`platform-messages`, `platform-servicing`) remains
the right choice when the handler has no async work.

## Schema

Dataclass with static type checks and dict/JSON helpers.

```python
from dataclasses import dataclass
from serpens.schema import Schema

@dataclass
class Person(Schema):
    name: str
    age: int

Person.load({"name": "Mike", "age": 18})
Person.loads('{"name": "Mike", "age": 18}')
Person("Mike", 18).dump()      # dict
Person("Mike", 18).dumps()     # JSON string
```

## CSV

```python
from serpens import csvutils as csv

for row in csv.open_csv_reader("fruits.csv"):
    print(row)

w = csv.open_csv_writer("out.csv")
w.writerow(["id", "name"]); w.writerow(["1", "Açaí"])
```

## Database

Thin layer over **SQLAlchemy 2.0**. Owns:

- Engine setup with production defaults (Postgres `statement_timeout` /
  `lock_timeout` / `idle_in_transaction_session_timeout`, Cloud SQL
  keepalives, scheme normalization, `pool_pre_ping` / `pool_use_lifo`,
  Lambda-aware tuning).
- Session factories (`SessionLocal`, `AsyncSessionLocal`).
- Declarative `Base` and `TimestampMixin`.
- Alembic helper (see [Migrations](#migrations)).
- Generic `Repository[T]` / `AsyncRepository[T]` covering the CRUD every
  service used to re-implement.

Query construction stays in `sqlalchemy` proper — the lib does not re-export
`select`, `Integer`, etc.

### Why use it

- **Production hardening baked in.** `statement_timeout`, `lock_timeout`,
  `idle_in_transaction_session_timeout`, Cloud SQL keepalives, pool tuning
  and `pool_pre_ping` apply automatically. Apps that hand-roll
  `create_engine(...)` skip this; the lib makes it the default.
- **One source of truth for engine config.** Pool size, recycle, LIFO
  checkout, Postgres timeouts — all env-driven, consistent across services.
  No more per-app drift on `max_overflow` or `pool_recycle`.
- **Symmetric sync/async.** `bind` / `async_bind`, `SessionLocal` /
  `AsyncSessionLocal`, `db_session` / `async_db_session`. Same mental
  model on either side; mix freely.
- **`Repository[T]` removes CRUD boilerplate.** PK lookup, filtered query,
  paginate, add, bulk_add, `upsert` (Postgres `ON CONFLICT RETURNING`),
  with deliberate gaps where services should diverge (no hard-delete, no
  partial update — see recipes).
- **Alembic glue.** `serpens.database.alembic.run_migrations(metadata)`
  drives migrations from a Lambda or CLI with one line in `env.py`.

### Migration scenarios

| Today's code | Move to | What you gain |
|---|---|---|
| Hand-rolled `create_engine(...) + sessionmaker(...)` (e.g. `platform-conciliation/src/common/database.py`) | `serpens.database.bind` + `SessionLocal` / `db_session` | Postgres timeouts, Cloud SQL keepalives, env-driven pool tuning, scheme normalization, `pool_pre_ping`, Lambda-aware defaults |
| Pony ORM (`platform-servicing`, `platform-messages`) | `serpens.database` + SQLAlchemy 2.0 | Async support, typed `Mapped[...]` columns, Alembic instead of yoyo, the SA 2.0 ecosystem; see [Migrating from Pony ORM](#migrating-from-pony-orm) |
| Per-service CRUD repositories (each app has its own `get_by_id`, `list`, `paginate`) | `serpens.database.Repository[T]` / `AsyncRepository[T]` | Shared base, `upsert` primitive for idempotency, NotFound exception, free pagination |
| Direct `redis.asyncio.Redis` + manual `aclose()` in DB-adjacent code | `serpens.database.async_bind` + `async_db_session` | Lifecycle helpers, autoflush=False, expire_on_commit=False sensible defaults |

Existing app to follow as POC: `platform-agreements` (full SA 2.0 + Alembic adoption is in `feat/migrate-pony-to-sqlalchemy`).

### Hello world (sync)

```python
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from serpens.database import Base, SessionLocal, TimestampMixin, bind


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


bind()  # reads DATABASE_URL

with SessionLocal() as sess:
    sess.add(User(name="Ana"))
    sess.commit()
```

### Hello world (async)

```python
from sqlalchemy import select
from serpens.database import async_bind, async_db_session

async_bind()  # reads DATABASE_URL, normalizes scheme to asyncpg

async def fetch(user_id: int):
    async with async_db_session() as sess:
        return (await sess.scalars(select(User).filter_by(id=user_id))).first()
```

Async requires `asyncpg` (Postgres) or `aiosqlite` (SQLite).

### Two ways to open a session

**Explicit (preferred).** `SessionLocal()` / `AsyncSessionLocal()` — caller owns
commit/rollback. FastAPI handlers should use the per-request dependency:

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from serpens.database import fastapi_session  # or fastapi_async_session

@app.get("/users/{id}")
def get_user(id: int, db: Session = Depends(fastapi_session)):
    return db.scalars(select(User).filter_by(id=id)).first()
```

**Auto-managed.** `db_session()` / `async_db_session()` — context managers that
commit on success, roll back on exception and close always. Convenient for
Lambda handlers and short scripts. Pass the session explicitly to helpers:

```python
from serpens.database import async_db_session

async def fetch(sess, user_id: int):
    return (await sess.scalars(select(User).filter_by(id=user_id))).first()

async with async_db_session() as sess:
    user = await fetch(sess, 1)
```

There is no `current_session()` global — sessions are passed.

### Schema scoping

```python
from serpens.database import declarative_base

Base = declarative_base(schema="public")
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | — | Connection string. `postgres://` and `postgresql://` are normalized to `postgresql+psycopg2://` (sync) / `postgresql+asyncpg://` (async). |
| `APP_NAME` | `serpens` | Postgres `application_name`. Overridden by `K_SERVICE` (Cloud Run) or `AWS_LAMBDA_FUNCTION_NAME` (Lambda). |
| `DB_POOL_SIZE` | `10` | Pool size. **Set to `1` on Lambda.** |
| `DB_MAX_OVERFLOW` | `20` | Extra connections. **Set to `0` on Lambda.** |
| `DB_POOL_TIMEOUT` | `10` | Seconds to wait for a free connection. |
| `DB_POOL_RECYCLE` | `1800` | Recycle older connections. |
| `DB_STATEMENT_TIMEOUT_MS` | `5000` | Postgres `statement_timeout`. |
| `DB_LOCK_TIMEOUT_MS` | `2000` | Postgres `lock_timeout`. |
| `DB_IDLE_IN_TX_TIMEOUT_MS` | `10000` | Postgres `idle_in_transaction_session_timeout`. |
| `DB_POOL_USE_LIFO` | `true` | LIFO checkout (warm connections preferred). Set `false` for FIFO. |
| `DB_ECHO` | `false` | Log every SQL statement. |

`bind()` and `async_bind()` also accept `pool_use_lifo=True/False` as a direct
override of the env var.

Cloud SQL keepalives (`keepalives=1`, `keepalives_idle=30`,
`keepalives_interval=10`, `keepalives_count=3`) are applied automatically on
Postgres connections.

### Bind from FastAPI lifespan, never at import time

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from serpens.database import async_bind, async_dispose

@asynccontextmanager
async def lifespan(_app: FastAPI):
    async_bind()
    yield
    await async_dispose()

app = FastAPI(lifespan=lifespan)
```

Calling `bind()` at the top of `models.py` makes import order matter and
breaks under cold-start.

### Repository (optional)

`Repository[T]` (sync) and `AsyncRepository[T]` (async) cover the CRUD that
every service rewrites: PK lookups, filtered queries, paginate, add, upsert.
Subclass with `model = X` and add your own methods for anything custom — the
`query` property exposes a `Select(model)` you compose on. The base
intentionally **does not** ship hard-delete or partial update: services do
soft-delete differently and updates often need optimistic locking.

```python
from serpens.database import AsyncRepository

class ProductRepo(AsyncRepository[Product]):
    model = Product

    async def by_slug(self, slug):                 # custom lookup
        return await self.get_by(slug=slug)

async with async_db_session() as sess:
    p = await ProductRepo(sess).by_slug("noverde_empirica")
```

Built-in methods: `get`, `get_or_raise` (raises `serpens.database.NotFound`),
`get_by`, `exists`, `count`, `list(order_by=, limit=, offset=, **filters)`,
`paginate(stmt=, page=, size=)`, `add(obj, flush=True)`, `bulk_add(objs)`,
`upsert(values, conflict_on=, update_fields=)`.

#### Recipe: soft-delete

Don't expose hard delete. Add a method on your repo:

```python
class PaymentRepo(AsyncRepository[Payment]):
    model = Payment

    async def cancel(self, payment, *, reason: str):
        payment.status = "cancelled"
        payment.cancel_reason = reason
        await self.sess.flush()
```

#### Recipe: optimistic locking

Declare `version_id_col` on the model — `Repository` doesn't fight it:

```python
class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    __mapper_args__ = {"version_id_col": version}
```

SA will raise `StaleDataError` on concurrent update. Catch it in the handler.

#### Recipe: idempotent insert (`upsert`, not `get_or_create`)

`get_or_create` has a race between SELECT and INSERT. Use `upsert` instead —
Postgres `INSERT ... ON CONFLICT ... RETURNING`:

```python
class IdempotentPaymentRepo(AsyncRepository[Payment]):
    model = Payment

await IdempotentPaymentRepo(sess).upsert(
    {"external_id": req.idempotency_key, "amount": req.amount, "status": "received"},
    conflict_on=["external_id"],
    update_fields=["amount"],   # omit to do nothing on conflict
)
```

## Migrations

**New repos use Alembic.** `serpens.migrations` (yoyo) is kept only for legacy
services that haven't migrated yet.

`serpens.database.alembic.run_migrations` wires Alembic against your app's
`Base.metadata` with sensible defaults (offline/online, scheme normalization to
psycopg2, `NullPool` to keep migration jobs from leaking pool slots).

`alembic/env.py`:

```python
from myapp.models import Base
from serpens.database.alembic import run_migrations

run_migrations(target_metadata=Base.metadata)
```

`alembic.ini` (minimal):

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
sqlalchemy.url =
```

Run with `DATABASE_URL` set:

```bash
alembic revision -m "add user table" --autogenerate
alembic upgrade head
```

For a Lambda migration job (no `alembic.ini` in the package):

```python
import os
from alembic import command
from alembic.config import Config

def migrate_handler(event, context):
    cfg = Config()
    cfg.set_main_option("script_location", os.path.dirname(os.path.abspath(__file__)))
    command.upgrade(cfg, "head")
```

Reference setup: [`platform-agreements/alembic`](https://github.com/DotzInc/platform-agreements/tree/main/alembic).

## Migrating from Pony ORM

Pony lacks async, lacks typed `Mapped[T]`, and is in limited maintenance. The
platform standardised on SQLAlchemy 2.0 via `serpens.database`. **Use the async
API by default** — `platform-agreements` is the reference and runs SA 2.0 async
end-to-end.

### Mapping table

| Pony | SQLAlchemy 2.0 + serpens |
|---|---|
| `class X(db.Entity):` | `class X(TimestampMixin, Base):` |
| `name = Required(str)` | `name: Mapped[str] = mapped_column(String, nullable=False)` |
| `email = Optional(str)` | `email: Mapped[str \| None] = mapped_column(String, nullable=True)` |
| `created_at = Required(datetime)` | inherit `TimestampMixin` |
| `loans = Set(lambda: Loan)` | `loans: Mapped[list["Loan"]] = relationship(back_populates="user")` |
| `composite_key(a, b)` | `__table_args__ = (UniqueConstraint("a", "b"),)` |
| `_table_ = ("public", "users")` | `__tablename__ = "users"; __table_args__ = {"schema": "public"}` |
| `@db_session` decorator | `with db_session()` block or pass `Session` |
| `X(field=value)` (auto-flush) | `obj = X(...); sess.add(obj); sess.flush()` |
| `X.get(field=value)` | `sess.scalars(select(X).filter_by(field=value)).first()` |
| `X.select(...).order_by(X.id)[:10]` | `sess.scalars(select(X).order_by(X.id).limit(10)).all()` |
| `X.select_by_sql("SELECT ...", params)` | `sess.scalars(select(X).from_statement(text("SELECT ..."))).all()` |
| `db.generate_mapping(create_tables=True)` | `Base.metadata.create_all(engine)` |

### Per-file recipe

Branch from `staging` → `feat/migrate-pony-to-sqlalchemy`.

1. **`requirements.txt`** — bump `noverde-serpens`, ensure `SQLAlchemy>=2.0`,
   add `asyncpg` (for async) and/or `psycopg2-binary` (for sync + Alembic),
   drop `pony` and `yoyo-migrations`.
2. **Models** — replace `db = Database()` and `class X(db.Entity)`. Methods
   stuck to the entity (`X.get_by_slug`, `X.create`) become module-level
   functions taking `Session` / `AsyncSession` as first argument:
   ```python
   async def get_product_by_slug(sess: AsyncSession, slug: str) -> Product | None:
       return (await sess.scalars(select(Product).filter_by(slug=slug))).first()
   ```
3. **Handlers** — open `async with async_db_session() as sess:` and pass `sess`
   down. In FastAPI routes use `Depends(fastapi_async_session)`.
4. **`main.py`** — `async_bind()` runs in a FastAPI `lifespan`, never at
   import time.
5. **Tests** — `setUp` uses `async with async_db_session() as sess: sess.add(...)`.
   `tearDown` uses `await sess.execute(delete(...))`. `testgres.setup(Base)`
   still works.
6. **Migrations** — yoyo → Alembic. Add `alembic.ini`, `alembic/env.py`
   delegating to `serpens.database.alembic.run_migrations`, and a baseline
   revision wrapping the existing schema with `IF NOT EXISTS`. Lambda
   `Migrate` switches to `Handler: migrate_handler.migrate_handler`. Run
   `alembic stamp 0001_baseline` once per environment.

### Common gotchas

- **Optimistic lock changes**. Pony locks read rows by default; SA 2.0 does
  not. If a job relied on it (e.g. `platform-servicing`), opt back in with
  `version_id_col` on the model.
- **`X(...)` does not INSERT in SA 2.0**. Use `sess.add(obj)` and, if you need
  `obj.id` populated, `sess.flush()`.
- **`autoflush=False`**. Serpens disables autoflush so a stray `select`
  doesn't flush pending changes. Call `sess.flush()` explicitly when needed.
- **Lambda pool**: `DB_POOL_SIZE=1`, `DB_MAX_OVERFLOW=0`. A larger pool
  causes Cloud SQL churn under burst.
- **`postgres://` vs `postgresql://`**: SA 2.0 dropped the short prefix.
  serpens normalises both.
- **Schema declaration**: pick one place — `declarative_base(schema=...)`
  centralized, or `__table_args__={"schema":...}` per model. Don't mix.

### When NOT to use serpens.database

- The repo already has an idiomatic SA 2.0 `SessionLocal` (e.g.
  `platform-conciliation`). Don't migrate just for standardization.
- You need an SA feature serpens does not expose — import from `sqlalchemy`
  directly. Serpens is a thin layer by design.

## DynamoDB

```python
from dataclasses import dataclass
from serpens.document import BaseDocument

@dataclass
class PersonDocument(BaseDocument):
    _table_name_ = "person"
    id: str
    name: str

PersonDocument(id="1", name="Ana").save()
PersonDocument.get_by_key({"id": "1"})
PersonDocument.get_table()
```

## Async HTTP client

Singleton `httpx.AsyncClient` — connection pools survive across requests.

```python
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from httpx import AsyncClient
from serpens.http_client import close_client, get_client, init_client

@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_client()
    yield
    await close_client()

app = FastAPI(lifespan=lifespan)

@app.get("/proxy")
async def proxy(client: AsyncClient = Depends(get_client)):
    return (await client.get("https://example.com")).json()
```

Timeout defaults to `HTTP_CLIENT_TIMEOUT` (env, seconds) or 30s. Extra kwargs
pass through to `httpx.AsyncClient`.

### Why use it

- **Pool reuse across requests.** A new `AsyncClient(...)` per request
  creates and tears down TCP+TLS connections every call. The singleton
  amortises the handshake across the lifetime of the process — material
  latency win on chatty integrations.
- **One lifecycle to wire.** `init_client` / `close_client` plug into
  FastAPI `lifespan` (or `startup`/`shutdown` for older versions). No
  per-handler instantiation boilerplate.
- **Env-driven timeout.** `HTTP_CLIENT_TIMEOUT` standardises the cap;
  per-service overrides through the same channel.

### Migration scenarios

| Today's code | Move to | What you gain |
|---|---|---|
| `async with httpx.AsyncClient() as client: await client.get(...)` per call | `init_client()` in lifespan + `get_client()` in handlers | Pool reuse, lower TCP/TLS overhead, central timeout |
| `requests.get(...)` (sync) inside a FastAPI handler | `init_client()` + `await client.get(...)` | Stops blocking the event loop for the duration of the call |
| Per-service `aiohttp` / `httpx` singleton with hand-rolled lifecycle | `serpens.http_client` | Shared implementation, one less file per repo |

Greenfield FastAPI services adopt this from day one; existing async services
swap a couple of imports.

## Rate limiter

Token-bucket limiter for outbound calls plus an `auth_lock` that serializes
token refresh (avoids thundering-herd re-auths on expiry).

```python
from serpens.rate_limit import RateLimiter

limiter = RateLimiter(rate=20, per_seconds=1.0)

@asynccontextmanager
async def lifespan(_app):
    limiter.start()
    yield
    await limiter.stop()

async def call_external():
    await limiter.acquire()
    return await client.get(...)

async def fetch_token():
    async with limiter.auth_lock:
        return await cached_get_or_set("token", 1800, _refresh_token)
```

### Why use it

- **Respects upstream quotas without manual back-off.** Most third-party
  APIs (banks, KYC providers, credit bureaus) cap requests-per-second;
  exceeding it triggers 429s or temporary blocks. Token bucket gives a
  smooth, predictable throughput at the configured ceiling.
- **`auth_lock` solves the thundering herd.** When a JWT/OAuth token
  expires, every concurrent coroutine tries to refresh at the same time.
  The lock guarantees one refresh per expiry while the rest wait on it.
- **Asyncio-native.** No third-party `aiolimiter` dependency; replenisher
  runs as an `asyncio.Task` you control via `start`/`stop`.

### Migration scenarios

| Today's code | Move to | What you gain |
|---|---|---|
| `asyncio.Semaphore(N)` hand-rolled to cap concurrency | `RateLimiter(rate=N, per_seconds=...)` | Time-based replenishment instead of pure concurrency cap; predictable RPS |
| `aiolimiter` / external rate-limit lib | `serpens.rate_limit` | One less dep; same primitive |
| No rate limiting at all (calls 3rd-party until 429) | `serpens.rate_limit` | Stops invalidating provider relationships and triggering exponential back-off cascades |
| Hand-rolled `asyncio.Lock` around token refresh | `limiter.auth_lock` | Bundled with the rate limit; less wiring |

Typical fit: any FastAPI / async service calling a quoted upstream
(banking, KYC, payment processor). Worth adopting alongside
`serpens.http_client` since they cover the same call path.

## Cache

`serpens.cache` ships three flavors in a single module. Pick by sync/async
and by scope (process-local vs distributed).

### Why use it

- **Fails open.** A Redis outage degrades to "no cache" instead of crashing
  the caller. Reads return `None` (treated as miss), writes/deletes become
  no-ops, decorators fall through to the wrapped function. Each failure
  logs a warning. This is the property the existing
  `fastapi_extras.databases.redis.RedisManager` does not provide.
- **Single source of truth.** Stops the per-service drift (in-process TTL
  caches reimplemented in each repo, Redis lifecycle wired by hand, etc.).
- **Symmetric APIs.** Sync, async in-process and async Redis share the
  same mental model: decorator-based caching plus low-level get/set/delete.
- **Lifecycle helpers built in** for the Redis flavor — `redis_init` /
  `redis_close` for module-level singleton usage, `redis_pool` for FastAPI
  `Depends` injection.
- **JSON serialization for free** on `redis_get` / `redis_set` /
  `redis_cached`; raw bytes are still available through `redis_pool`
  when needed.

### Migration scenarios

| Today's code | Move to | What you gain |
|---|---|---|
| `fastapi_extras.databases.redis.RedisManager` as `Depends` factory | `serpens.cache.redis_pool` | Fail-open client on Redis outage; same `Depends` contract, one-line swap |
| App-local `acached` / in-process async TTL cache (e.g. `platform-agreements/agreements/cache.py`) | `serpens.cache.acached` | One implementation maintained centrally; monotonic-clock TTL; same `self`-aware key heuristic |
| Direct `Redis.from_url(...)` + manual `aclose()` in Lambda | `serpens.cache.redis_init` / `redis_close` / `redis_get` / `redis_set` / `redis_cached` | Lifecycle helpers, auto JSON serialization, fail-open, env-driven prefix/TTL |
| `serpens.cache.cached` (sync legacy) | unchanged | Already lives here; consumed by `parameters` and `secrets_manager` |

The migration is intentionally minimal — typically a single import line per app. The behavior gain (Redis outages no longer break callers) is automatic on the new APIs.

### Sync, in-process (legacy)

Used by `serpens.parameters`, `serpens.secrets_manager` and downstream
services. TTL bucketed by name.

```python
from serpens.cache import cached, clear_cache

@cached("secrets_manager", 900)
def get(secret_id):
    ...

clear_cache("secrets_manager")
```

### Async, in-process

`acached` / `clear_acache` — same idea, for `async def` callers. The
decorator drops the first positional argument from the key, on the
assumption it's `self` (a repository or service object pointing at the
same store). Different instances therefore share entries — fine for
read-mostly data. Uses `time.monotonic` so TTL is immune to clock
adjustments.

```python
from serpens.cache import acached, clear_acache

class ProductRepo:
    @acached("products", ttl_seconds=600)
    async def get_by_slug(self, slug: str):
        return await self.session.scalar(select(Product).where(Product.slug == slug))

clear_acache("products")  # one bucket
clear_acache()            # everything
```

### Async, Redis-backed

For FastAPI / long-running services that need a cache shared across
workers and instances. Lifecycle: `redis_init` once at startup,
`redis_close` at shutdown.

**Fails open.** On `RedisError` (host unreachable, timeout, refused
connection) reads return `None` (treated as miss), writes/deletes become
no-ops, and `redis_cached_get_or_set` falls through to the wrapped
function. Each failure logs a warning. Programming errors (using the
client before `redis_init`) still raise `RuntimeError`.

```python
from serpens.cache import (
    redis_init, redis_close, redis_get, redis_set, redis_delete,
    redis_cached, redis_cached_get_or_set,
)

@asynccontextmanager
async def lifespan(_app):
    await redis_init()
    yield
    await redis_close()

await redis_set("user:42", {"name": "Ana"}, ttl=60)
user = await redis_get("user:42")

@redis_cached("products", ttl=600)
async def get_product(slug: str):
    return await fetch_product(slug)
```

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_URL` | — | Redis connection string. |
| `CACHE_PREFIX` | `serpens` | Prefix prepended to every key. Set per-service. |
| `CACHE_TTL` | `300` | Default TTL for `redis_set` / `redis_cached`. |

#### FastAPI `Depends` style

`redis_pool(url)` returns a callable suitable for FastAPI `Depends`,
yielding a fail-open Redis client per request. The same fail-open
semantics apply: `get` returns `None`, `set`/`delete` no-op on
`RedisError`.

```python
from fastapi import Depends, FastAPI
from redis.asyncio import Redis
from serpens.cache import redis_pool

app = FastAPI()
cache = redis_pool(settings.REDIS_URL)

@app.get("/users/{user_id}")
async def get_user(user_id: str, client: Redis = Depends(cache)):
    return await client.get(f"user:{user_id}")
```

Use this when the rest of the app expects a `redis.asyncio.Redis`
client (e.g. when wiring third-party libraries that take `cache_gen`).
For Lambda / single-process apps, the `redis_*` module-level functions
above are simpler.

#### In tests

`testgres.setup(Base, redis_mode=True)` spins a Redis container alongside
Postgres and exports `REDIS_URL` — `redis_init()` picks it up without
further config. If `REDIS_URL` is already set, the existing instance is
reused.

## Async Pub/Sub publisher

`serpens.pubsub.AsyncPublisher` wraps the sync Google SDK with
`asyncio.wrap_future` so `await publish(...)` does not block the event loop.
Instantiate once per process in `lifespan`, close on shutdown.

`topic` is the full topic id (`projects/PROJECT/topics/NAME`) — the same value
Terraform exposes as an env var, no need to rebuild it via
`client.topic_path(...)`. When `elasticapm` is installed, every publish emits a
messaging span labeled with the topic.

```python
from serpens.pubsub import AsyncPublisher

publisher = AsyncPublisher()

@asynccontextmanager
async def lifespan(_app):
    yield
    publisher.close()

async def emit(payload: dict):
    await publisher.publish(settings.MY_TOPIC, payload)
```

### Why use it

- **Doesn't block the event loop.** The Google SDK is synchronous (returns
  a `concurrent.futures.Future`). Without `asyncio.wrap_future`, awaiting
  a publish in a FastAPI handler stalls every other request on the same
  worker. `AsyncPublisher` bridges the gap.
- **Terraform-friendly topic id.** Accepts `projects/.../topics/...`
  directly — same value already exposed as `MY_TOPIC` env in your
  Terraform module. No need to keep `project_id` separately and call
  `client.topic_path(project, topic)` everywhere.
- **APM observability for free.** When `elasticapm` is installed, every
  publish emits a `messaging` span with `queue_name=<topic>`. No-op if
  APM isn't present.
- **Single connection per process.** The client is instantiated once on
  app boot; gRPC channel reuse cuts per-publish overhead.

### Migration scenarios

| Today's code | Move to | What you gain |
|---|---|---|
| `pubsub_v1.PublisherClient()` + `client.topic_path(project, topic)` + `future.result()` per publish (`platform-servicing` patterns) | `AsyncPublisher()` + `await publisher.publish(topic, payload)` | Non-blocking publish, full topic id, central APM span emission, one client per process |
| `serpens.pubsub.publish_message(...)` (sync, creates a new `PublisherClient` per call) inside an async handler | `AsyncPublisher` | Avoids the per-call client construction; no event loop blocking |
| Two services with their own `TracedMessagePublisher` wrapper (e.g. `integrator-vcom`) | `AsyncPublisher` | Removes the duplicated wrapper; spans emitted from the lib |

The sync `serpens.pubsub.publish_message` / `publish_message_batch` remain
the right choice for Lambda one-shots or non-async code paths.

## Test infrastructure (testgres)

`serpens.testgres.setup` wires a Postgres (and optionally Redis) container
into a `unittest`/`pytest` suite, running `create_all` against your
`Base.metadata` before the first test.

```python
# conftest.py
from serpens import testgres
from myapp.models import Base

testgres.setup(Base, async_mode=True, redis_mode=True)
```

### Modes

| Flag | Effect | When to enable |
|---|---|---|
| (default) | Spins a Postgres container, binds `database.SessionLocal` (sync) | Lambda services / sync codebases |
| `async_mode=True` | Also binds `database.AsyncSessionLocal` with `NullPool` | FastAPI services / async tests; remove the per-conftest async engine wiring |
| `redis_mode=True` | Spins a Redis container alongside Postgres, exports `REDIS_URL` | Services using `serpens.cache.redis_*` or `fastapi_extras` Redis; replaces the manual `docker run redis` boilerplate that lives in `pix-automatic` / `integrator-vcom` test setup |
| `default_schema="x,y"` | Pre-creates the schemas and sets `search_path` | Services using schema scoping via `declarative_base(schema=...)` |
| `uri=...` / `DATABASE_URL` env | Skips the container, uses the provided URI | CI runners that already have Postgres available |
| `REDIS_URL` env (when `redis_mode=True`) | Skips the Redis container, uses the provided URL | CI runners with existing Redis |

### Why use it

- **One conftest line replaces a dozen.** Tests that previously wired
  `create_engine`, `metadata.create_all`, `sessionmaker`, container
  lifecycle, schema setup and Redis container setup collapse to a single
  `setup(...)` call.
- **Real Postgres in tests.** Caught the kind of bug SQLite can't model
  (`ON CONFLICT`, `JSONB` operators, schema-qualified names). Same engine
  semantics as production.
- **Async + sync engines wired together.** Both `SessionLocal` and
  `AsyncSessionLocal` point at the same database — tests can mix.
- **Defers `create_all` to `startTestRun`.** Models registered after
  `setup()` returns (common when tests do dynamic imports) still get
  their tables.
- **Graceful failure.** Waits for the published TCP port and a real
  `psycopg2.connect`, raising a clear `RuntimeError` if the container
  doesn't come up — no more silent test hangs.

### Migration scenarios

| Today's code | Move to | What you gain |
|---|---|---|
| Hand-rolled `docker run postgres:13` in test setup + manual `create_engine` + `metadata.create_all` | `serpens.testgres.setup(Base)` | Container lifecycle, schema bootstrap, sane defaults, error propagation |
| Test suite that wires async engine separately from sync (parallel `AsyncSessionLocal` setup in `conftest.py`) | `setup(Base, async_mode=True)` | One factory wired automatically with `NullPool` (correct for tests) |
| `pix-automatic` / `integrator-vcom` style: `docker run postgres` + `docker run redis` boilerplate in `conftest.py` | `setup(Base, redis_mode=True)` | One call, both containers, env vars exported |
