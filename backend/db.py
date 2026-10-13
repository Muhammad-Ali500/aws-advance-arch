"""
DynamoDB access for user-submitted "items" - partition key user_sub, sort
key item_id, so each user's items are naturally isolated and efficiently
queryable without a scan.

DYNAMODB_ENDPOINT_URL is only set for local testing against DynamoDB Local;
left unset in production so boto3 talks to the real regional AWS endpoint -
same code either way, same pattern as storage.py in the gcp-traditional-arch
project's AWS port.
"""
import datetime
import logging
import os
import uuid

import boto3

logger = logging.getLogger("backend.db")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "aws-advance-arch-items")
ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL") or None
REGION = os.environ.get("AWS_REGION", "us-east-1")

_resource = boto3.resource(
    "dynamodb",
    region_name=REGION,
    endpoint_url=ENDPOINT_URL,
    # DynamoDB Local doesn't check these, but boto3 requires *something* to
    # be set - real AWS deployments get real credentials from the ECS task
    # role instead, which take precedence whenever they're actually present.
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "local"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "local"),
)
_table = _resource.Table(TABLE_NAME)


def create_item(user_sub: str, text: str) -> dict:
    item = {
        "user_sub": user_sub,
        "item_id": str(uuid.uuid4()),
        "text": text,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    _table.put_item(Item=item)
    return item


def list_items(user_sub: str) -> list:
    resp = _table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("user_sub").eq(user_sub)
    )
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
