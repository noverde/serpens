# serpens

A set of Python utilities, recipes and snippets.

- [SQS Utilities](#sqs-utilities)
- [API Utilities](#api-utilities)
- [Schema](#schema)
- [CSV Utils](#csv-utils)
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

- The function that will process the lambda will receive an instance of *sqs.Request* dataclass. This class has the follow structure:

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

This utilities are useful for working with database.

##### Migrate databases

- This migrations use yoyo-migration.

```python
from serpens import database

database_url = "postgres://user:password@host/db"
path = "/path/to/migrations" # yoyo migrations

database.migrate(database_url, path)
```

##### Create a Pony Database instance

"*The Database object manages database connections using a connection pool.*"

```python
from serpens import database

database_url = "postgres://user:password@host/db"
db = database.setup(database_url)
print(db.provider_name)
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