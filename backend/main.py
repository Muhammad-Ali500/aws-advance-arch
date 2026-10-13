"""
Backend API - validates AWS Cognito JWT access tokens.

Points at either real AWS Cognito (prod, on ECS) or cognito-local (local
Docker testing) purely via environment variables - no code branching. Same
container image either way.
"""
import logging
import os
import time

import requests
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel

import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(title="AWS Advance Arch - Backend API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

COGNITO_ISSUER = os.environ.get("COGNITO_ISSUER", "")
COGNITO_JWKS_URL = os.environ.get("COGNITO_JWKS_URL", "")
COGNITO_APP_CLIENT_IDS = {
    c.strip() for c in os.environ.get("COGNITO_APP_CLIENT_IDS", "").split(",") if c.strip()
}
ADMIN_GROUP_NAME = os.environ.get("ADMIN_GROUP_NAME", "Admins")

_jwks_cache = {"keys": None, "fetched_at": 0.0}
JWKS_CACHE_TTL_SECONDS = 3600


def _get_jwks():
    now = time.time()
    if _jwks_cache["keys"] is None or now - _jwks_cache["fetched_at"] > JWKS_CACHE_TTL_SECONDS:
        resp = requests.get(COGNITO_JWKS_URL, timeout=5)
        resp.raise_for_status()
        _jwks_cache["keys"] = resp.json()["keys"]
        _jwks_cache["fetched_at"] = now
        logger.info("Refreshed JWKS from %s", COGNITO_JWKS_URL)
    return _jwks_cache["keys"]


def verify_token(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1]

    try:
        unverified_headers = jwt.get_unverified_header(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(401, f"Invalid token header: {exc}") from exc

    keys = _get_jwks()
    key = next((k for k in keys if k["kid"] == unverified_headers.get("kid")), None)
    if key is None:
        raise HTTPException(401, "Signing key not found in JWKS")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=COGNITO_ISSUER,
            # Cognito ACCESS tokens carry the app client id as `client_id`, not
            # the usual `aud` claim - checked manually below instead.
            options={"verify_aud": False},
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(401, f"Token verification failed: {exc}") from exc

    if claims.get("token_use") != "access":
        raise HTTPException(401, "Not an access token")

    token_client_id = claims.get("client_id") or claims.get("aud")
    if COGNITO_APP_CLIENT_IDS and token_client_id not in COGNITO_APP_CLIENT_IDS:
        raise HTTPException(401, "Token was not issued by a recognized app client (dev-ui or dev-admin)")

    return claims


def require_admin(claims: dict = Depends(verify_token)) -> dict:
    groups = claims.get("cognito:groups", [])
    if ADMIN_GROUP_NAME not in groups:
        raise HTTPException(403, f"Requires membership in the '{ADMIN_GROUP_NAME}' group")
    return claims


@app.get("/api/public")
def public():
    return {"ok": True, "message": "Backend is reachable - no auth required"}


@app.get("/api/me")
def me(claims: dict = Depends(verify_token)):
    return {
        "sub": claims.get("sub"),
        "username": claims.get("username"),
        "groups": claims.get("cognito:groups", []),
        "token_use": claims.get("token_use"),
    }


class ItemBody(BaseModel):
    text: str


@app.post("/api/items")
def create_item(body: ItemBody, claims: dict = Depends(verify_token)):
    item = db.create_item(claims["sub"], body.text)
    return {"ok": True, "item": item}


@app.get("/api/items")
def list_items(claims: dict = Depends(verify_token)):
    return db.list_items(claims["sub"])


@app.get("/api/admin/stats")
def admin_stats(claims: dict = Depends(require_admin)):
    return {
        "ok": True,
        "message": f"Hello admin '{claims.get('username')}' - this endpoint required the '{ADMIN_GROUP_NAME}' group",
        "stats": {"total_items_in_dynamodb": db.count_all_items()},
    }
