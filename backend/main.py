"""
Basic practice backend. The code is intentionally simple; what matters is
that each endpoint exercises one piece of the Slotta AWS infrastructure:

  GET  /health                 -> ALB target group + ECS container health check (port 3000)
  POST /auth/login             -> Cognito app client (ADMIN_USER_PASSWORD_AUTH) + task role
  GET  /api/me                 -> Cognito JWT verification (JWKS)
  GET/POST /api/items          -> DynamoDB + task role
  GET  /api/admin/stats        -> Cognito groups (SUPER_ADMIN / ADMIN)
  GET  /api/admin/check/s3     -> S3 bucket (presigned upload URL)
  GET  /api/admin/check/sqs    -> SQS queue
  GET  /api/admin/check/kms    -> KMS key
  GET  /api/admin/check/secrets-> Secrets Manager (loaded at boot)
  GET  /api/admin/check/egress -> NAT Gateway (internet from private subnets)

Env var names match the real Slotta backend.
"""
import logging
import os
import time
import uuid

import requests
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel

import app_secrets
import aws_clients
import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

REGION = aws_clients.REGION
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
# Derived from the pool on real AWS; override only needed for cognito-local.
COGNITO_ISSUER = os.environ.get("COGNITO_ISSUER") or f"https://cognito-idp.{REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
COGNITO_JWKS_URL = os.environ.get("COGNITO_JWKS_URL") or f"{COGNITO_ISSUER}/.well-known/jwks.json"
ADMIN_GROUPS = ("SUPER_ADMIN", "ADMIN")

LOGO_BUCKET = os.environ.get("LOGO_BUCKET", "")
WAITLIST_EVENTS_QUEUE_URL = os.environ.get("WAITLIST_EVENTS_QUEUE_URL", "")
CALENDAR_TOKENS_KMS_KEY_ID = os.environ.get("CALENDAR_TOKENS_KMS_KEY_ID", "")

# Comma-separated allowed browser origins (your two Amplify domains).
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

app = FastAPI(title="Slotta dummy backend")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    # Like the real backend: missing secret / IAM permission stops the task at boot.
    app_secrets.load()


# --- auth helpers -----------------------------------------------------------
_jwks = {"keys": None, "at": 0.0}


def verify_token(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if _jwks["keys"] is None or time.time() - _jwks["at"] > 3600:
        _jwks["keys"] = requests.get(COGNITO_JWKS_URL, timeout=5).json()["keys"]
        _jwks["at"] = time.time()
    try:
        kid = jwt.get_unverified_header(token).get("kid")
        key = next(k for k in _jwks["keys"] if k["kid"] == kid)
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=COGNITO_ISSUER, options={"verify_aud": False})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(401, f"Invalid token: {exc}") from exc
    if claims.get("token_use") != "access" or claims.get("client_id") != COGNITO_CLIENT_ID:
        raise HTTPException(401, "Wrong token type or app client")
    return claims


def require_admin(claims: dict = Depends(verify_token)) -> dict:
    if not set(claims.get("cognito:groups", [])) & set(ADMIN_GROUPS):
        raise HTTPException(403, "Requires SUPER_ADMIN or ADMIN group")
    return claims


def not_configured(env_var: str):
    raise HTTPException(503, f"not configured: set {env_var} on the ECS task")


# --- endpoints --------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/public")
def public():
    return {"message": "backend reachable"}


class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def login(body: LoginBody):
    try:
        resp = aws_clients.client("cognito-idp").admin_initiate_auth(
            UserPoolId=COGNITO_USER_POOL_ID,
            ClientId=COGNITO_CLIENT_ID,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": body.email.strip(), "PASSWORD": body.password},
        )
    except Exception as exc:  # noqa: BLE001
        err = getattr(exc, "response", {}).get("Error", {})
        logger.warning("login failed for %s: %s", body.email.strip(), err.get("Code", type(exc).__name__))
        raise HTTPException(401, f"login failed: {err.get('Code', type(exc).__name__)} - {err.get('Message', '')}") from exc
    if "AuthenticationResult" not in resp:
        # e.g. NEW_PASSWORD_REQUIRED: set a permanent password in the Cognito console.
        raise HTTPException(400, f"challenge not supported in dummy app: {resp.get('ChallengeName')}")
    return {"access_token": resp["AuthenticationResult"]["AccessToken"]}


@app.get("/api/me")
def me(claims: dict = Depends(verify_token)):
    return {"sub": claims["sub"], "username": claims.get("username"), "groups": claims.get("cognito:groups", [])}


class ItemBody(BaseModel):
    text: str


@app.post("/api/items")
def create_item(body: ItemBody, claims: dict = Depends(verify_token)):
    return db.create_item(claims["sub"], body.text)


@app.get("/api/items")
def list_items(claims: dict = Depends(verify_token)):
    return db.list_items(claims["sub"])


@app.get("/api/admin/stats")
def admin_stats(claims: dict = Depends(require_admin)):
    return {"total_items": db.count_all_items()}


@app.get("/api/admin/check/s3")
def check_s3(claims: dict = Depends(require_admin)):
    if not LOGO_BUCKET:
        not_configured("LOGO_BUCKET")
    url = aws_clients.client("s3").generate_presigned_url(
        "put_object", Params={"Bucket": LOGO_BUCKET, "Key": f"logos/{uuid.uuid4()}.png"}, ExpiresIn=300
    )
    return {"ok": True, "presigned_put_url": url}


@app.get("/api/admin/check/sqs")
def check_sqs(claims: dict = Depends(require_admin)):
    if not WAITLIST_EVENTS_QUEUE_URL:
        not_configured("WAITLIST_EVENTS_QUEUE_URL")
    resp = aws_clients.client("sqs").send_message(QueueUrl=WAITLIST_EVENTS_QUEUE_URL, MessageBody='{"test": true}')
    return {"ok": True, "message_id": resp["MessageId"]}


@app.get("/api/admin/check/kms")
def check_kms(claims: dict = Depends(require_admin)):
    if not CALENDAR_TOKENS_KMS_KEY_ID:
        not_configured("CALENDAR_TOKENS_KMS_KEY_ID")
    kms = aws_clients.client("kms")
    blob = kms.encrypt(KeyId=CALENDAR_TOKENS_KMS_KEY_ID, Plaintext=b"hello")["CiphertextBlob"]
    return {"ok": kms.decrypt(CiphertextBlob=blob)["Plaintext"] == b"hello"}


@app.get("/api/admin/check/secrets")
def check_secrets(claims: dict = Depends(require_admin)):
    return {"ok": True, "source": app_secrets.SECRETS_SOURCE, "keys": sorted(app_secrets.load())}


@app.get("/api/admin/check/egress")
def check_egress(claims: dict = Depends(require_admin)):
    try:
        return {"ok": True, "public_ip": requests.get("https://checkip.amazonaws.com", timeout=5).text.strip()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, "no internet from the task - private subnet without NAT?") from exc
