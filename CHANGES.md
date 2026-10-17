# Changes made to align the dummy project's infrastructure with Slotta (2026-10-16)

The app is still basic. These changes are only about the **infrastructure shape**.

## Infra mismatches fixed

| Area | Before | Now (matches Slotta) |
|---|---|---|
| Container port / health | 8080, health check on `/api/public` | **3000**, `GET /health`, Docker `HEALTHCHECK` + ECS container health check, `curl` in the image, non-root user |
| Networking | Tasks in **public** subnets with public IPs, no NAT | Tasks in **private** subnets, **NAT Gateway**, S3 + DynamoDB gateway endpoints |
| Cognito | 2 app clients, self sign-up, group `Admins`, browser-side login (`USER_PASSWORD_AUTH`) | **1 public client (no secret)**, no self sign-up, groups **SUPER_ADMIN / ADMIN**, login through the backend with **`ADMIN_USER_PASSWORD_AUTH`** |
| Secrets | none | **Secrets Manager** secret loaded at boot (`LOCAL_SECRETS=true` only for local) |
| Extra AWS services | none | **S3** (presigned URL), **SQS** `waitlist-events` + DLQ, **KMS** key, each with a check endpoint |
| IAM | task role only had 3 DynamoDB actions | `aws/backend-task-role-policy.json` covers DynamoDB, Cognito, Secrets, S3, SQS and KMS (least privilege) |
| Env var names | `COGNITO_ISSUER`, `COGNITO_APP_CLIENT_IDS`, … | Same names as Slotta: `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `LOGO_BUCKET`, `WAITLIST_EVENTS_QUEUE_URL`, `CALENDAR_TOKENS_KMS_KEY_ID` |
| Backend CI/CD | GitHub Actions with long-lived IAM user keys, auto on push | **CodePipeline + CodeBuild** with root `buildspec.yml` (nothing hardcoded). GitHub workflow kept as a **manual-only** alternative using **OIDC** |
| dev-ui hosting | Static Vite site | **Next.js 15 SSR** (Amplify `WEB_COMPUTE`), like slotta-fe, so you practise SSR hosting + wildcard subdomains |
| dev-admin | Inline `<style>`, no security headers | Strict **CSP headers** in `amplify.yml` like slotta-admin-ui (styles moved to a file so CSP doesn't block them) |
| Amplify build spec | Per-folder `amplify.yml` only | Root **monorepo** `amplify.yml` (`applications:` + `appRoot`) |
| ALB | HTTP only, default 60 s idle timeout | Guide adds an **HTTPS track** (Route 53 + ACM + `api.` domain) and **idle timeout 120 s**. Backend keep-alive set to 130 s |

## Bugs found and fixed (these would have broken the AWS deployment)
1. **`npm ci` would fail on Amplify:** neither frontend had a `package-lock.json`. Both have one now.
2. **DynamoDB calls would fail on ECS:** `db.py` passed placeholder credentials (`"local"`) whenever the env vars were missing, which overrides the ECS task role. Credentials are now only passed when pointing at a local emulator (`backend/aws_clients.py`).
3. **Task would fail to start:** the task definition used `awslogs-create-group: true`, but `AmazonECSTaskExecutionRolePolicy` doesn't allow `logs:CreateLogGroup`. The log group is now created manually (guide Phase 10).
4. **S3 presigned URLs:** forced SigV4 + regional endpoint. The legacy global endpoint redirects for new buckets, which breaks browser uploads.

## Fixes from the local end-to-end run
5. Login errors now show Cognito's real reason (e.g. `NotAuthorizedException`), and the email is trimmed.
6. Both UIs declare an empty inline favicon, so browsers stop logging a 404 on every page load.
7. `.gitignore` now ignores `.next/` and `next-env.d.ts`, so Next.js build output isn't committed.

## Files
- **Rewritten:** `backend/main.py`, `backend/db.py`, `backend/Dockerfile`, `aws/backend-task-def.json`, `.github/workflows/deploy-backend.yml`, `docker-compose.local.yml`, `local-testing/seed_cognito_local.py`, `local-testing/get_test_tokens.py`, `dev-admin/*`, `dev-ui/*`, `AWS_DEPLOYMENT_GUIDE.md`, `README.md`
- **New:** `backend/aws_clients.py`, `backend/app_secrets.py`, `backend/.dockerignore`, `aws/backend-task-role-policy.json`, `buildspec.yml`, `amplify.yml`, `local-testing/test_backend_moto.py`, `dev-admin/src/style.css`, `dev-ui/app/*`, `dev-ui/next.config.mjs`, lockfiles
- **Moved, not deleted:** the original Vite `dev-ui` → `_archive/dev-ui-vite-original/`, an unused tenant middleware → `_archive/dev-ui-extra/`
- **Unchanged:** `cost.txt`. Its estimate doesn't include the NAT Gateway (~$0.045/h + data), the KMS key (~$1/month, prorated) or the secret (~$0.40/month, prorated).

## Verified
- Backend: `local-testing/test_backend_moto.py` passes all checks offline (login, 401/403 rules, DynamoDB, S3, SQS, KMS, Secrets).
- `dev-admin`: `npm run build` OK; the built HTML has no inline script/style (CSP-safe).
- `dev-ui`: production `next build` OK under Node 20 (run via `npx node@20`; the machine's own Node 18.12 is too old). `/` builds as a dynamic (SSR) route.
- Full browser end-to-end test in Microsoft Edge against both **production builds**: 23/23 checks passed (login, 401/403 rules, every infra check, SSR, items in DynamoDB, no console errors). The `API_PROXY_TARGET` (no-domain) proxy in dev-ui works too.
- Not tested locally: the backend **Docker image** (Docker Desktop wasn't running) and Amplify's own rewrite rules (they only exist on Amplify).
- Nothing was created in AWS, and no git commands that change anything were run. Committing and pushing is up to you.
