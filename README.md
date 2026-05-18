# serpens

Shared Python building blocks for DotzInc services: thin layers over SQLAlchemy
2.0, Redis, httpx, Pub/Sub, SQS and friends. The lib stays out of the way —
apps import the underlying SDKs directly for the heavy lifting and use serpens
for the configuration that should not be duplicated across 24 repos.

- [SQS](#sqs) · [Lambda API](#lambda-api) · [Schema](#schema) · [CSV](#csv)
- [Database](#database) · [Migrations](#migrations) · [Pony → SQLAlchemy](#migrating-from-pony-orm)
- [DynamoDB](#dynamodb) · [Async HTTP](#async-http-client) · [Rate limiter](#rate-limiter)
- [Async Redis cache](#async-redis-cache) · [Async Pub/Sub](#async-pubsub-publisher)

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

Query construction stays in `sqlalchemy` proper — the lib does not re-export
`select`, `Integer`, etc.

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
| `DB_ECHO` | `false` | Log every SQL statement. |

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

## Async Redis cache

Async, Redis-backed counterpart of `serpens.cache` (which is in-memory). Use
in FastAPI / long-running services that need a shared cache across workers.

```python
from serpens.cache_async import cached, cached_get_or_set, close, delete, get, init, set_

@asynccontextmanager
async def lifespan(_app):
    await init()
    yield
    await close()

await set_("user:42", {"name": "Ana"}, ttl=60)
user = await get("user:42")

@cached("products", ttl=600)
async def get_product(slug: str):
    return await fetch_product(slug)
```

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_URL` | — | Redis connection string. |
| `CACHE_PREFIX` | `serpens` | Prefix prepended to every key. Set per-service. |
| `CACHE_TTL` | `300` | Default TTL for `set_` / `cached`. |

## Async Pub/Sub publisher

`serpens.pubsub.AsyncPublisher` wraps the sync Google SDK with
`asyncio.wrap_future` so `await publish(...)` does not block the event loop.
Instantiate once per process in `lifespan`, close on shutdown.

```python
from serpens.pubsub import AsyncPublisher

publisher = AsyncPublisher(project_id=settings.GCP_PROJECT_ID)

@asynccontextmanager
async def lifespan(_app):
    yield
    publisher.close()

async def emit(payload: dict):
    await publisher.publish("my-topic", payload)
```
