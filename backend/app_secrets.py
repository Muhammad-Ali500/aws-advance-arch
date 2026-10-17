"""
Loads one JSON secret from AWS Secrets Manager (APP_SECRET_ID, default
"slotta-dummy/app"), like the real backend's slotta/* secrets.
LOCAL_SECRETS=true reads it from the APP_SECRET_JSON env var instead (local only, never on ECS).
"""
import json
import os

import aws_clients

APP_SECRET_ID = os.environ.get("APP_SECRET_ID", "slotta-dummy/app")
USE_LOCAL = os.environ.get("LOCAL_SECRETS") == "true"
SECRETS_SOURCE = "env (LOCAL_SECRETS=true)" if USE_LOCAL else "aws-secrets-manager"

_cache = None


def load() -> dict:
    global _cache
    if _cache is None:
        if USE_LOCAL:
            raw = os.environ.get("APP_SECRET_JSON", '{"api_key": "local-dev"}')
        else:
            raw = aws_clients.client("secretsmanager").get_secret_value(SecretId=APP_SECRET_ID)["SecretString"]
        _cache = json.loads(raw)
    return _cache
