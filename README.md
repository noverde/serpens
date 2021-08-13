# serpens

A set of Python utilities, recipes and snippets

- [SQS Utilities](#sqs-utilities)
- [API Utilities](#api-utilities)
- [Schema](#schema)
- [CSV Utils](#csv-utils)

## SQS Utilities

- This utility is a decorator that iterate by each sqs record.

- For each sqs record will be inserted de *record object (from type sqs.Record)* as  argument that will to process the sqs messages.


```python
from serpens import sqs

@sqs.handler
def message_processor(record: sqs.Record):
    # code to process each sqs message
    print(record.body)
```

### Record

- The function that will process each sqs message receive a instance of *sqs.Record* dataclass. This class has the follow structure:

```python
class Record:
    message_id: UUID
    receipt_handle: str
    body: Union[str, dict]
    attributes: Attributes
    message_attributes: dict
    md5_of_message_attributes: str
    md5_of_body: str
    event_source: str
    event_source_arn: EventSourceArn
    aws_region: str

class Attributes:
    approximate_receive_count: int
    sent_timestamp: datetime
    sender_id: str
    approximate_first_receive_timestamp: datetime

class EventSourceArn:
    raw: str
    queue_name: str # is a property
```

## API Utilities

- This utility is a wrapper for simplify the work with lambda handlers. The decorator ```api.handler``` will decorate a function that will process a lambda and this function will receive a ```request``` argument (from type api.Request).


```python
from serpens import api

@api.handler
def lambda_handler(request: api.Request):
    # Code to process the lambda
    print(request.body)
```

#### *Request class*

- The function that will process the lambda will receive a instance of *sqs.Request* dataclass. This class has the follow structure:

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

- *Note*: the objects from type ```AttrDict``` are objects built by a dict where the key from dict is a attribute of object. For example:

```python
from serpens.api import AttrDict

obj = AttrDict({"foo": "bar"})
obj.foo # bar
```

## Schema
- The Schema is a base class for create new classes with follow features:
> - Static type check
> - Method for convert a object to dict
> - Method for create a object from json
> - Method for create object from dict
> - Method for dumps a object to string

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

This utilities are useful for works with database. At this moment exists two function for ....

```python
from serpens import database

database_url = "postgres://user:password@host/db"
path = "/path/to/migrations" # yoyo migrations

database.migrate(database_url, path)
```

```python
from serpens import database

database_url = "postgres://user:password@host/db"
db = database.setup(database_url)
print(db.provider_name)
```