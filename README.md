# aws-advance-arch

A test architecture: two frontends (**dev-ui** for end users, **dev-admin**
for admins) deployed to **AWS Amplify Hosting**, a **FastAPI backend** on
**ECS Fargate** behind an **Application Load Balancer**, and **AWS Cognito**
for user management (one User Pool, two App Clients, an "Admins" group for
role-based access control).

See `cost.txt` for the full real-pricing cost estimate (~3 hour test) and
`AWS_DEPLOYMENT_GUIDE.md` for the complete, concept-by-concept Console
walkthrough.

## Architecture

```
dev-ui (Amplify) --\
                     \
dev-admin (Amplify) --+--> backend (ECS Fargate, behind ALB) --> Cognito (JWT verification)
```

Both frontends authenticate directly against Cognito (client-side, via
`amazon-cognito-identity-js`) and call the backend with the resulting JWT
access token. The backend verifies the token's signature against Cognito's
JWKS and checks `cognito:groups` for admin-only endpoints.

## Services

- `dev-ui/` - end-user app: sign up, confirm, sign in, call `/api/me`
- `dev-admin/` - admin app: sign in (no self-signup), call `/api/admin/stats`
  (requires "Admins" group membership)
- `backend/` - FastAPI, verifies Cognito JWTs, two protected endpoints plus
  one public health check

## Local testing (already done, all passing)

Uses [`cognito-local`](https://github.com/jagregory/cognito-local) to
emulate real AWS Cognito locally - same code, zero changes needed to point
at real Cognito later.

```bash
# 1. Start cognito-local
cd local-testing
docker build -f cognito-local.Dockerfile -t cognito-local-test .
docker run -d -p 9229:9229 --name cognito-local-run cognito-local-test

# 2. Seed it with a User Pool, both App Clients, an Admins group, and 2 test users
cd ..
pip install boto3
python local-testing/seed_cognito_local.py
# ^ prints the exact IDs/env values you need for the next steps

# 3. Build + run the backend with those values
cd backend
docker build -t aws-advance-arch-backend .
docker run -d -p 8080:8080 \
  -e COGNITO_ISSUER="http://localhost:9229/<POOL_ID>" \
  -e COGNITO_JWKS_URL="http://host.docker.internal:9229/<POOL_ID>/.well-known/jwks.json" \
  -e COGNITO_APP_CLIENT_IDS="<DEV_UI_CLIENT_ID>,<DEV_ADMIN_CLIENT_ID>" \
  --name backend-test aws-advance-arch-backend

# 4. Build + run each frontend (Vite bakes these in at BUILD time)
cd ../dev-ui
docker build \
  --build-arg VITE_USER_POOL_ID="<POOL_ID>" \
  --build-arg VITE_USER_POOL_CLIENT_ID="<DEV_UI_CLIENT_ID>" \
  --build-arg VITE_COGNITO_ENDPOINT="http://localhost:9229" \
  -t aws-advance-arch-dev-ui .
docker run -d -p 5173:5173 --name dev-ui-test aws-advance-arch-dev-ui
# repeat the same pattern for dev-admin on port 5174, with its own client ID
```

Open http://localhost:5173 (dev-ui) - sign up, confirm (cognito-local
prints the verification code to its own container logs instead of sending
a real email - `docker logs cognito-local-run`), sign in, call the API.

Test accounts seeded automatically: `testuser@example.com` / `TestPass123!`
(regular) and `testadmin@example.com` / `TestPass123!` (in the Admins group).

**Verified working end-to-end before pushing:** full auth/authorization
matrix tested via curl with real tokens from cognito-local - public access,
401 with no token, 200 with a valid user token, 403 for a non-admin calling
the admin endpoint, 200 for an admin calling it, and 401 for a malformed
token. Both frontends confirmed to build correctly with their own isolated
Cognito client IDs baked in (dev-admin's build does not contain dev-ui's
client ID, and vice versa).

## Deployment

See `AWS_DEPLOYMENT_GUIDE.md` for the full Console walkthrough: Cognito
User Pool + Groups + App Clients, ECS + ALB for the backend, and both
Amplify Hosting apps (including the rewrite rule that proxies `/api/*` to
the backend so the HTTPS frontend never directly calls the HTTP backend -
avoiding browser mixed-content blocking without needing a custom domain).
