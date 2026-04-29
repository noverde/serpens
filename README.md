# serpens

A set of Python utilities, recipes and snippets.

- [SQS Utilities](#sqs-utilities)
- [API Utilities](#api-utilities)
- [Schema](#schema)
- [CSV Utils](#csv-utils)
- [Database](#database)
- [Migrations](#migrations)
- [Migrating from Pony ORM](#migrating-from-pony-orm)
- [DynamoDB Documents](#dynamodb-documents)

## SQS Utilities

- This utility is a decorator that iterate by each sqs record.

- For each sqs record will be inserted a *record object (from type sqs.Record)* as  argument that will process the sqs messages.


```python
from serpens import sqs

@sqs.handler
def message_processor(record: sqs.Record):
    # code to process each sqs message
    print(record.body)
```

### Record

- The client function that will process the sqs messages will receive an instance of *sqs.Record* dataclass. This class has the follow structure:

```python
class Record:
    data: Dict[Any, Any]
    body: Union[dict, str]
    message_attributes: Dict[Any, Any]
    queue_name: str
    sent_datetime: datetime
```
##### Record attributes
- **data**: Contain all data from SQS message. This attribute is assigned in each iteration in SQS message.
- **body**: Return ```data["body"]``` converted to ```dict``` or ```str```.
- **message_attributes**: Return the ```data["messageAttributes"]``` converted to ```dict```.
- **queue_name**: Return the queue name extracted from ```data["eventSourceARN"]```.
- **sent_datetime**: Return the ```data["attributes"]["SentTimestamp"]``` converted to ```datetime```.

## API Utilities

- This utility is a wrapper to simplify working with lambda handlers. The decorator ```api.handler``` will decorate a function that will process a lambda and this function will receive a ```request``` argument (from type api.Request).


```python
from serpens import api

@api.handler
def lambda_handler(request: api.Request):
    # Code to process the lambda
    print(request.body)
```

#### *Request class*

- The function that will process the lambda will receive an instance of *api.Request* dataclass. This class has the follow structure:

```python
from serpens.api import AttrDict

class Request:
    authorizer: AttrDict
    body: Union[str, dict]
    path: AttrDict
    query: AttrDict
    headers: AttrDict
    identity: AttrDict
```

- *Note*: the objects from type ```AttrDict``` are objects built by a dict where the dict's key is an attribute of object. For example:


```python
from serpens.api import AttrDict

obj = AttrDict({"foo": "bar"})
obj.foo # bar
```

## Schema
- The Schema is a base class for create new classes with follow features:
> - Static type check
> - Method to convert an object to dict
> - Method to create an object from json
> - Method to create an object from dict
> - Method to dump an object to string

##### Create a schema

```python
from serpens.schema import Schema
from dataclasses import dataclass

@dataclass
class PersonSchema(Schema):
    name: str
    age: int
```
##### Create a schema object

```python
person = PersonSchema('Mike', 30)

print(person.name)
print(person.age)
```

##### Create a schema object from a dict.

```python
person_obj = PersonSchema.load({'name': 'Mike', 'age': 18})

print(person_obj.name)
print(person_obj.age)
```

##### Create a schema object from a json string.

```python
import json
data = json.dumps({'name': 'mike', 'age': 20})
person_obj = PersonSchema.loads(data)

print(person_obj.name)
print(person_obj.age)
```

##### Convert a schema object to dict.

```python
p1 = PersonSchema('Mike', 30)
person_dct = PersonSchema.dump(p1)

print(person_dct['name'])
print(person_dct['age'])
```

##### Convert a schema object to json string.

```python
p1 = PersonSchema('Mike', 30)
person_str = PersonSchema.dumps(p1)

print(person_str)
```

## CSV Utils

- Utility for read and write csv. This utility is useful for read csv with BOM or read csv encoded as ISO-8859. 

##### Read CSV

```python
from serpens import csvutils as csv

dict_reader = csv.open_csv_reader('fruits_iso8859.csv')

for record in dict_reader:
    print(record)
```

##### Write CSV

```python
from serpens import csvutils as csv

writer = csv.open_csv_writer('out.csv')
writer.writerow(["id", "name"])
writer.writerow(["1", "Açaí"])

del writer
```

## Database

A thin layer over **SQLAlchemy 2.0**. Owns:

- Engine setup with production defaults (Postgres `statement_timeout` / `lock_timeout` / `idle_in_transaction_session_timeout`, Cloud SQL keepalives, scheme normalization, `pool_pre_ping` / `pool_use_lifo`, Lambda-aware tuning).
- The session factory (`SessionLocal`, `AsyncSessionLocal`).
- The declarative `Base` and `TimestampMixin`.
- An Alembic helper (see [Migrations](#migrations)).

Everything else — query construction (`select`, `update`, …), column types, relationship loaders — comes from `sqlalchemy` **directly**. The lib does not re-export them; importing `from sqlalchemy import select, Integer, String` is the idiomatic SA 2.0 way.

### Hello world

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

with SessionLocal() as sess:
    rows = sess.scalars(select(User).filter_by(name="Ana")).all()
```

### Two ways to open a session

**1. Explicit (preferred)** — `SessionLocal()`. Caller owns commit/rollback. Use this in FastAPI handlers via `Depends`:

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from serpens.database import SessionLocal

def get_db() -> Session:
    with SessionLocal() as db:
        yield db

@app.get("/users/{id}")
def get_user(id: int, db: Session = Depends(get_db)):
    return db.scalars(select(User).filter_by(id=id)).first()
```

**2. Auto-managed (Lambda / scripts)** — `db_session()`. A `@contextmanager` that commits on success, rolls back on exception, and closes the session always. Auto-binds if `bind()` was not called.

```python
from serpens.database import db_session

with db_session() as sess:
    sess.add(User(name="Ana"))
# commit on exit, rollback on exception, close always
```

`db_session()` is a regular Python context manager — no singleton, no `current_session()` global. Pass the `Session` argument explicitly to helper functions:

```python
def fetch(sess: Session, user_id: int) -> User | None:
    return sess.scalars(select(User).filter_by(id=user_id)).first()

with db_session() as sess:
    user = fetch(sess, 1)
```

### Models

`Base` is a `DeclarativeBase`. `TimestampMixin` adds `created_at` / `updated_at`, refreshing `updated_at` on every UPDATE.

```python
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from serpens.database import Base, TimestampMixin

class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
```

For repos where every table lives under a single Postgres schema:

```python
from serpens.database import declarative_base

Base = declarative_base(schema="public")
```

### Async

Symmetric API: `async_bind()`, `async_dispose()`, `AsyncSessionLocal`, `async_db_session()`. The same Postgres timeout listener is registered against the async engine's underlying sync engine, so `statement_timeout` / `lock_timeout` / `idle_in_transaction_session_timeout` apply to async connections too.

```python
from sqlalchemy import select
from serpens.database import async_bind, async_db_session

async_bind()  # reads DATABASE_URL, normalizes scheme to asyncpg


async def fetch_user(user_id: int):
    async with async_db_session() as sess:
        stmt = select(User).where(User.id == user_id)
        return (await sess.scalars(stmt)).first()
```

Requires `asyncpg` (Postgres) or `aiosqlite` (SQLite).

### Configuration

Engine tuning via environment variables.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | — | Connection string. `postgres://` and `postgresql://` are normalized to `postgresql+psycopg2://` (sync) / `postgresql+asyncpg://` (async). |
| `APP_NAME` | `serpens` | Postgres `application_name`. Overridden by `K_SERVICE` (Cloud Run) or `AWS_LAMBDA_FUNCTION_NAME` (Lambda) when present. |
| `DB_POOL_SIZE` | `10` | Base connection pool size. **Set to `1` on Lambda.** |
| `DB_MAX_OVERFLOW` | `20` | Extra connections beyond `pool_size`. **Set to `0` on Lambda.** |
| `DB_POOL_TIMEOUT` | `10` | Seconds to wait for a free connection before failing. |
| `DB_POOL_RECYCLE` | `1800` | Recycle connections older than N seconds. |
| `DB_STATEMENT_TIMEOUT_MS` | `5000` | Postgres `statement_timeout` per session. |
| `DB_LOCK_TIMEOUT_MS` | `2000` | Postgres `lock_timeout` per session. |
| `DB_IDLE_IN_TX_TIMEOUT_MS` | `10000` | Postgres `idle_in_transaction_session_timeout`. |
| `DB_ECHO` | `false` | Log every SQL statement (debug only). |

Keepalives (`keepalives=1`, `keepalives_idle=30`, `keepalives_interval=10`, `keepalives_count=3`) are applied automatically on Postgres connections — required for Cloud SQL behind NAT.

### Bind from FastAPI lifespan, not import-time

`bind()` reads `DATABASE_URL` at call time. Calling it from the top-level of `models.py` makes import order matter and breaks if envvars aren't set yet. Use a lifespan context:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from serpens.database import bind, dispose

@asynccontextmanager
async def lifespan(_app: FastAPI):
    bind()
    yield
    dispose()

app = FastAPI(lifespan=lifespan)
```

## Migrations

**New repos should pick Alembic.** `serpens.migrations` (yoyo) is kept for legacy repos but is no longer the recommended path.

### Alembic (recommended)

`serpens.database.alembic.run_migrations` wires Alembic against your app's `Base.metadata` with sensible defaults (offline/online modes, scheme normalization to psycopg2, `NullPool` to avoid leaking pool slots during migration jobs).

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

Run with `DATABASE_URL` set in the environment:

```bash
alembic revision -m "add user table" --autogenerate
alembic upgrade head
```

For a Lambda migration job, build the Alembic `Config` in-memory so you don't need `alembic.ini` in the deployment package:

```python
import os
from alembic import command
from alembic.config import Config

def migrate_handler(event, context):
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = Config()
    cfg.set_main_option("script_location", here)
    command.upgrade(cfg, "head")
```

A complete reference setup lives in [`platform-agreements`](https://github.com/DotzInc/platform-agreements/tree/main/alembic) — that repo is the migration POC and shows the full structure (`env.py`, `versions/`, Lambda handler, baseline revision, cutover from yoyo).

### yoyo-migrations (legacy)

Existing repos that haven't migrated yet keep using yoyo:

```python
from serpens import migrations

migrations.migrate("postgresql://user:password@host/db", "/path/to/migrations")
```

Lambda handler that reads `DATABASE_URL` and `DATABASE_MIGRATIONS_PATH`:

```python
# template.yml / SAM
Handler: serpens.migrations.migrate_handler
```

## Migrating from Pony ORM

Pony ORM works but is no longer actively maintained, lacks async support and SA 2.0's typed `Mapped[]` API. The Dotz platform standardized on **SQLAlchemy 2.0 via `serpens.database`**. This is the recipe for moving an existing Pony-based service to SA 2.0.

> **Reference POC**: [`DotzInc/platform-agreements`](https://github.com/DotzInc/platform-agreements/pull/409) — read that PR end-to-end before starting your own. Models, handlers, tests, Alembic baseline, Lambda migrate handler, cutover playbook are all there.

### Mapping table — Pony → SQLAlchemy 2.0

| Pony | SQLAlchemy 2.0 + serpens |
|---|---|
| `class X(db.Entity):` | `class X(Base):` |
| `name = Required(str)` | `name: Mapped[str] = mapped_column(String, nullable=False)` |
| `email = Optional(str)` | `email: Mapped[str \| None] = mapped_column(String, nullable=True)` |
| `created_at = Required(datetime)` | inherit `TimestampMixin` |
| `loans = Set(lambda: Loan)` | `loans: Mapped[list["Loan"]] = relationship(back_populates="user")` |
| `composite_key(a, b)` | `__table_args__ = (UniqueConstraint("a", "b"),)` |
| `_table_ = ("public", "users")` | `__tablename__ = "users"; __table_args__ = {"schema": "public"}` |
| `@db_session` (Pony decorator) | `with db_session() as sess:` block, or pass `Session` argument |
| `X(field=value)` (auto-flush) | `obj = X(field=value); sess.add(obj); sess.flush()` |
| `X.get(field=value)` | `sess.scalars(select(X).filter_by(field=value)).first()` |
| `X.select(field=value).order_by(X.id)[:10]` | `sess.scalars(select(X).filter_by(field=value).order_by(X.id).limit(10)).all()` |
| `X.select_by_sql("SELECT ...", params)` | `sess.scalars(select(X).from_statement(text("SELECT ..."))).all()` |
| `commit()` / `rollback()` | implicit on `with db_session()` (or call `sess.commit()` / `sess.rollback()` with `SessionLocal()`) |
| `db.generate_mapping(create_tables=True)` | `Base.metadata.create_all(engine)` |

### Per-file recipe

Apply this to a typical Pony service (`gateway-authorizer`, `platform-disbursement`, etc.). Branch from `staging` → `feat/migrate-pony-to-sqlalchemy`.

1. **`requirements.txt`** — bump `noverde-serpens`, ensure `SQLAlchemy>=2.0` + `psycopg2-binary` are present, drop `pony` and `yoyo-migrations` (the latter only after you switch to Alembic).
2. **Models (`models.py`)** — replace `db = Database()` and `class X(db.Entity)` per the mapping table. Functions that used to be `@staticmethod`s on the entity (`X.get_by_slug(...)`, `X.create(...)`) become **module-level functions that take `Session` as the first argument**:
   ```python
   def get_product_by_slug(sess: Session, slug: str) -> Product | None:
       return sess.scalars(select(Product).filter_by(slug=slug)).first()
   ```
   This is what makes the codebase idiomatic SA. See [`platform-agreements/agreements/models.py`](https://github.com/DotzInc/platform-agreements/blob/feat/migrate-pony-to-sqlalchemy/agreements/models.py) for the full pattern.
3. **Handlers (`handlers.py`)** — open `with db_session() as sess:` and pass `sess` down:
   ```python
   @api.handler
   def get_agreements(request):
       with db_session() as sess:
           product = get_product_by_slug(sess, settings.DEFAULT_PRODUCT_SLUG)
           agreements = get_current_agreements(sess, kinds, product.id)
       return [serialize(a) for a in agreements]
   ```
4. **`main.py`** — move `bind()` out of any `models.py` import-side call into a FastAPI `lifespan`:
   ```python
   @asynccontextmanager
   async def lifespan(_app):
       bind()
       yield
       dispose()
   app = FastAPI(lifespan=lifespan)
   ```
5. **Tests** — `setUp`/fixtures stop relying on Pony's auto-flush:
   ```python
   def setUp(self):
       with db_session() as sess:
           sess.add(Product(...))
           sess.flush()
   def tearDown(self):
       with db_session() as sess:
           sess.execute(delete(Product))
   ```
   `testgres.setup(database.Base)` keeps working unchanged.
6. **Migrations** — yoyo → Alembic. Drop `migrations/*.sql`, drop `yoyo.ini`. Add `alembic.ini`, `alembic/env.py` (delegates to `serpens.database.alembic.run_migrations`), and a baseline revision that wraps your existing schema with `IF NOT EXISTS` for idempotency. The Lambda `Migrate` function in `template.yml` switches `Handler: serpens.migrations.migrate_handler` (yoyo) for `Handler: migrate_handler.migrate_handler` (Alembic). One-time per environment, run `alembic stamp 0001_baseline` against the live DB so Alembic recognizes the existing schema.

### Common gotchas

- **Optimistic lock changes behavior**. Pony silently locks any row you read inside a session if its non-volatile fields change before commit. SA 2.0 does **not** do this by default. If a job depended on it (e.g. avoiding double-processing in `platform-servicing`), opt back in with SA's `version_id_col` on the model.
- **`X(...)` does not INSERT in plain SA 2.0**. You must `sess.add(obj)`, and `sess.flush()` if you need `obj.id` populated immediately. Tests that relied on Pony's auto-flush will fail otherwise.
- **`autoflush=False`**. Serpens disables autoflush so a stray `select` doesn't trigger flush of pending changes mid-transaction. If you need flushed state visible, call `sess.flush()` explicitly.
- **Lambda pool**: set `DB_POOL_SIZE=1`, `DB_MAX_OVERFLOW=0`. A pool larger than 1 is not just useless on Lambda — it provokes Cloud SQL connection churn under burst.
- **`postgres://` vs `postgresql://`**: SA 2.0 dropped the legacy short prefix. serpens normalizes both, but envvars copied between repos still need attention.
- **Don't `bind()` at import time**. `bind()` reads `DATABASE_URL` from the environment. Calling it from the top-level of `models.py` makes import order matter. Use FastAPI's `lifespan` context.
- **Schema declaration — pick one place**. Either `Base = declarative_base(schema="public")` (centralized) or `__table_args__={"schema":"public"}` per model. Mixing both causes confusion when you start using `MetaData.reflect`.

### When NOT to use serpens.database

- Your repo is already SA 2.0 idiomatic with its own `SessionLocal` pattern (e.g. `platform-conciliation`). The lib doesn't add value over what you have. **Don't migrate just for the sake of standardization.**
- You need an SA feature serpens doesn't expose. Import from `sqlalchemy` directly — serpens is intentionally a thin layer and stays out of the way.

## DynamoDB Documents

Serpens provides a base class (called *BaseDocument*) for working with tables from DynamoDB. 

##### Create a document mapping a DynamoDB table

```python
from serpens.document import BaseDocument
from dataclasses import dataclass

@dataclass
class PersonDocument(BaseDocument):
    _table_name_ = 'person'
    id: str
    name: str
```

##### Save data in DynamoDB table

```python
person = PersonDocument(id="1", name="Ana")
person.save()
```

##### Get data from key

- Obs: If the search doesn't find an item by its key, the return is ```None```

```python
person = PersonDocument.get_by_key({"id": "1"})

person.id # 1
person.name # Ana
```

##### Get table

```python
person_table = PersonDocument.get_table()
person_table # dynamodb.Table(name='person')
```