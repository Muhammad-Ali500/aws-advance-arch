"""
DynamoDB access for user-submitted "items" - partition key user_sub, sort
key item_id, so each user's items are naturally isolated and efficiently
queryable without a scan.

DYNAMODB_ENDPOINT_URL is only set for local testing against DynamoDB Local;
left unset on ECS so boto3 talks to the real regional endpoint with the
task role's credentials (see aws_clients.py).
"""
import datetime
import logging
import os
import uuid

from boto3.dynamodb.conditions import Key

import aws_clients

logger = logging.getLogger("backend.db")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "aws-advance-arch-items")

_table = aws_clients.resource("dynamodb").Table(TABLE_NAME)


def create_item(user_sub: str, text: str) -> dict:
    item = {
        "user_sub": user_sub,
        "item_id": str(uuid.uuid4()),
        "text": text,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _table.put_item(Item=item)
    return item


def list_items(user_sub: str) -> list:
    resp = _table.query(KeyConditionExpression=Key("user_sub").eq(user_sub))
    items = resp.get("Items", [])
    items.sort(key=lambda i: i.get("created_at", ""), reverse=True)
    return items


def count_all_items() -> int:
    """Full-table scan - fine for a demo admin stats panel at this scale.
    A real production app would maintain a counter or use DynamoDB Streams
    instead of scanning the whole table on every admin page load."""
    count = 0
    resp = _table.scan(Select="COUNT")
    count += resp["Count"]
    while "LastEvaluatedKey" in resp:
        resp = _table.scan(Select="COUNT", ExclusiveStartKey=resp["LastEvaluatedKey"])
        count += resp["Count"]
    return count
