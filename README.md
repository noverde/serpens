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