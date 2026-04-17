# serpens

A set of Python utilities, recipes and snippets.

- [SQS Utilities](#sqs-utilities)
- [API Utilities](#api-utilities)
- [Schema](#schema)
- [CSV Utils](#csv-utils)
- [Database](#database)
- [Migrations](#migrations)
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

- A thin layer on top of SQLAlchemy 2.0 that keeps a Pony-like ergonomic API while exposing SA 2.0 power.

##### Declare models

```python
from serpens.database import Base, EntityMixin, TimestampMixin, Integer, Mapped, String, mapped_column


class User(EntityMixin, TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
```

TimestampMixin adds created_at and updated_at, refreshing updated_at on every UPDATE.

##### Open sessions

- db_session works as context manager and decorator. Nested calls reuse the outermost session.

```python
from serpens.database import db_session


with db_session:
    user = User.get(name="Ana")


@db_session
def create_user(name):
    return User(name=name)
```

##### Query with select()

- select, insert, update, delete, func, text, bindparam and loading strategies (joinedload, selectinload, contains_eager) are re-exported.

```python
from serpens.database import db_session, select


with db_session as sess:
    stmt = select(User).where(User.name.like("A%")).order_by(User.created_at.desc())
    users = sess.scalars(stmt).all()
```

- EntityMixin offers a Pony-style shortcut:

```python
user = User.get(name="Ana")
matches = User.select(active=True).order_by(User.name).all()
```

##### Bulk insert

```python
from serpens.database import bulk_insert

bulk_insert(User, [{"name": "Ana"}, {"name": "Bia"}, {"name": "Caio"}])
```

##### Async sessions

- async_db_session mirrors db_session. Works as async with and decorator.

```python
from serpens.database import async_bind, async_db_session, current_async_session, select


async_bind("postgresql://user:pw@host/db")


@async_db_session
async def fetch_user(user_id):
    sess = current_async_session()
    stmt = select(User).where(User.id == user_id)
    return (await sess.scalars(stmt)).first()
```

- Requires asyncpg for Postgres or aiosqlite for SQLite.

##### Configuration

- Engine tuning is read from environment variables.

| Variable | Default | Purpose |
|---|---|---|
| DATABASE_URL | — | Connection string (supports postgres:// and postgresql://) |
| DB_POOL_SIZE | 10 | Base connection pool size |
| DB_MAX_OVERFLOW | 20 | Extra connections beyond pool_size |
| DB_POOL_TIMEOUT | 10 | Seconds to wait for a free connection before failing |
| DB_POOL_RECYCLE | 1800 | Recycle connections older than N seconds |
| DB_STATEMENT_TIMEOUT_MS | 5000 | Postgres statement_timeout per session |
| DB_LOCK_TIMEOUT_MS | 2000 | Postgres lock_timeout per session |
| DB_IDLE_IN_TX_TIMEOUT_MS | 10000 | Postgres idle_in_transaction_session_timeout |
| DB_ECHO | false | Log every SQL statement (debug only) |

- Keepalives for Cloud SQL are applied automatically on Postgres connections.
- For AWS Lambda, set DB_POOL_SIZE=1 and DB_MAX_OVERFLOW=0 — Lambda does not reuse the pool across concurrent containers.

## Migrations

- Schema evolution with yoyo-migrations.

```python
from serpens import migrations

database_url = "postgres://user:password@host/db"
path = "/path/to/migrations"

migrations.migrate(database_url, path)
```

- A ready-made Lambda handler reads DATABASE_URL and DATABASE_MIGRATIONS_PATH from the environment:

```python
# in template.yml / SAM
Handler: serpens.migrations.migrate_handler
```

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