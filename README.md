# serpens

A set of Python utilities, recipes and snippets

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
    queue_name: str
```