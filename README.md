# serpens

A set of Python utilities, recipes and snippets

- [API Utilities](api-utilities)
- [SQS Utilities](sqs-utilities)

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