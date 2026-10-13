"""
Creates the items table in DynamoDB Local - partition key user_sub, sort
key item_id, matching backend/db.py exactly. For real AWS, create the same
table via the Console (see AWS_DEPLOYMENT_GUIDE.md) instead of this script.
"""
import boto3

client = boto3.client(
    "dynamodb",
    endpoint_url="http://localhost:8500",
    region_name="us-east-1",
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

TABLE_NAME = "aws-advance-arch-items"

existing = client.list_tables().get("TableNames", [])
if TABLE_NAME in existing:
    print(f"Table '{TABLE_NAME}' already exists - nothing to do.")
else:
    client.create_table(
        TableName=TABLE_NAME,
        AttributeDefinitions=[
            {"AttributeName": "user_sub", "AttributeType": "S"},
            {"AttributeName": "item_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "user_sub", "KeyType": "HASH"},
            {"AttributeName": "item_id", "KeyType": "RANGE"},
        ],
        BillingMode="PAY_PER_REQUEST",  # on-demand, matches the real AWS table's mode
    )
    print(f"Created table '{TABLE_NAME}'.")
