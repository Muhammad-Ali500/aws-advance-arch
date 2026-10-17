"""Offline smoke test of the backend against moto (in-process AWS mock).
No Docker, no AWS account, no real AWS calls.

  pip install -r ../backend/requirements.txt "moto[cognitoidp]" httpx
  python -I test_backend_moto.py ../backend
"""
import json
import os
import sys

os.environ.update(AWS_REGION="us-east-1", AWS_DEFAULT_REGION="us-east-1",
                  AWS_ACCESS_KEY_ID="testing", AWS_SECRET_ACCESS_KEY="testing",
                  LOGO_BUCKET="dummy-logo")

from moto import mock_aws  # noqa: E402

mock_aws().start()
import boto3  # noqa: E402

cog = boto3.client("cognito-idp")
pool = cog.create_user_pool(PoolName="p")["UserPool"]["Id"]
client_id = cog.create_user_pool_client(UserPoolId=pool, ClientName="web",
                                        ExplicitAuthFlows=["ALLOW_ADMIN_USER_PASSWORD_AUTH"])["UserPoolClient"]["ClientId"]
cog.create_group(GroupName="ADMIN", UserPoolId=pool)
for email, group in (("user@example.com", None), ("admin@example.com", "ADMIN")):
    cog.admin_create_user(UserPoolId=pool, Username=email, MessageAction="SUPPRESS")
    cog.admin_set_user_password(UserPoolId=pool, Username=email, Password="TestPass123!", Permanent=True)
    if group:
        cog.admin_add_user_to_group(UserPoolId=pool, Username=email, GroupName=group)

boto3.client("dynamodb").create_table(
    TableName="aws-advance-arch-items", BillingMode="PAY_PER_REQUEST",
    AttributeDefinitions=[{"AttributeName": "user_sub", "AttributeType": "S"}, {"AttributeName": "item_id", "AttributeType": "S"}],
    KeySchema=[{"AttributeName": "user_sub", "KeyType": "HASH"}, {"AttributeName": "item_id", "KeyType": "RANGE"}])
boto3.client("secretsmanager").create_secret(Name="slotta-dummy/app", SecretString=json.dumps({"api_key": "x"}))
boto3.client("s3").create_bucket(Bucket="dummy-logo")
queue = boto3.client("sqs").create_queue(QueueName="waitlist-events")["QueueUrl"]
key = boto3.client("kms").create_key()["KeyMetadata"]["Arn"]
os.environ.update(COGNITO_USER_POOL_ID=pool, COGNITO_CLIENT_ID=client_id,
                  WAITLIST_EVENTS_QUEUE_URL=queue, CALENDAR_TOKENS_KMS_KEY_ID=key)

sys.path.insert(0, sys.argv[1])
from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

fails = 0


def check(name, cond):
    global fails
    fails += 0 if cond else 1
    print(("PASS " if cond else "FAIL ") + name)


with TestClient(main.app) as c:
    def tok(email):
        r = c.post("/auth/login", json={"email": email, "password": "TestPass123!"})
        return {"Authorization": "Bearer " + r.json()["access_token"]}

    u, a = tok("user@example.com"), tok("admin@example.com")
    check("health", c.get("/health").status_code == 200)
    check("me without token -> 401", c.get("/api/me").status_code == 401)
    check("me", c.get("/api/me", headers=u).status_code == 200)
    check("create + list item", c.post("/api/items", json={"text": "hi"}, headers=u).status_code == 200
          and len(c.get("/api/items", headers=u).json()) == 1)
    check("admin stats as user -> 403", c.get("/api/admin/stats", headers=u).status_code == 403)
    check("admin stats as ADMIN", c.get("/api/admin/stats", headers=a).status_code == 200)
    for svc in ("s3", "sqs", "kms", "secrets"):
        check(f"check/{svc}", c.get(f"/api/admin/check/{svc}", headers=a).json().get("ok") is True)

print("ALL PASSED" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
