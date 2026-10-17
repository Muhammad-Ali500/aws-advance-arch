"""
Shared boto3 client factory.

On AWS (ECS) no endpoint overrides are set, so boto3 uses the regional AWS
endpoints and picks up credentials from the ECS task role automatically.

For local testing (cognito-local, DynamoDB Local) the *_ENDPOINT_URL env vars
point at the emulators. Only in that case do we pass placeholder credentials:
passing explicit credentials on AWS would OVERRIDE the task role and every
call would fail with an invalid-signature error.
"""
import os

import boto3
from botocore.config import Config

REGION = os.environ.get("AWS_REGION", "us-east-1")

# Presigned S3 URLs must be SigV4 against the REGIONAL endpoint. The legacy
# global endpoint 307-redirects for freshly created buckets, and a redirect
# on a browser PUT fails CORS.
_S3_CONFIG = Config(signature_version="s3v4", s3={"addressing_style": "virtual"})

_ENDPOINT_ENV = {
    "dynamodb": "DYNAMODB_ENDPOINT_URL",
    "cognito-idp": "COGNITO_ENDPOINT_URL",
}


def _kwargs(service: str) -> dict:
    kwargs = {"region_name": REGION}
    if service == "s3":
        kwargs["config"] = _S3_CONFIG
        kwargs["endpoint_url"] = f"https://s3.{REGION}.amazonaws.com"
    endpoint = os.environ.get(_ENDPOINT_ENV.get(service, ""), "") or None
    if endpoint:
        kwargs["endpoint_url"] = endpoint
        if not os.environ.get("AWS_ACCESS_KEY_ID"):
            kwargs["aws_access_key_id"] = "local"
            kwargs["aws_secret_access_key"] = "local"
    return kwargs


def client(service: str):
    return boto3.client(service, **_kwargs(service))


def resource(service: str):
    return boto3.resource(service, **_kwargs(service))
