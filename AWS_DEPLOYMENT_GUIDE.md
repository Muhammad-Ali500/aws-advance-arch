# aws-advance-arch — Complete AWS Deployment Guide

Two frontends on **Amplify Hosting**, a **FastAPI backend** on **ECS
Fargate** behind an **Application Load Balancer**, and **AWS Cognito** for
user management — explained concept-by-concept, click-by-click, for
someone building this on AWS for the first time.

---

## Table of contents

1. [Architecture, and why each piece exists](#1-architecture-and-why-each-piece-exists)
2. [Glossary — every AWS concept used here](#2-glossary--every-aws-concept-used-here)
3. [Prerequisites](#3-prerequisites)
4. [Cost summary](#4-cost-summary)
5. [Where things stand already](#5-where-things-stand-already)
6. [Step 1 — Create the Cognito User Pool](#6-step-1--create-the-cognito-user-pool)
7. [Step 2 — Create the VPC, subnets, and security groups](#7-step-2--create-the-vpc-subnets-and-security-groups)
8. [Step 3 — Create the ECR repository and IAM execution role](#8-step-3--create-the-ecr-repository-and-iam-execution-role)
9. [Step 4 — Wire up GitHub Actions for the backend's CI/CD](#9-step-4--wire-up-github-actions-for-the-backends-cicd)
10. [Step 5 — Create the ECS cluster, task definition, and service behind an ALB](#10-step-5--create-the-ecs-cluster-task-definition-and-service-behind-an-alb)
11. [Step 6 — Deploy dev-ui to Amplify Hosting](#11-step-6--deploy-dev-ui-to-amplify-hosting)
12. [Step 7 — Deploy dev-admin to Amplify Hosting](#12-step-7--deploy-dev-admin-to-amplify-hosting)
13. [Step 8 — Test it end-to-end](#13-step-8--test-it-end-to-end)
14. [Step 9 — Troubleshooting](#14-step-9--troubleshooting)
15. [Step 10 — Teardown (delete everything)](#15-step-10--teardown-delete-everything)
16. [Appendix: how a request flows through this system](#16-appendix-how-a-request-flows-through-this-system)

---

## 1. Architecture, and why each piece exists

```
 Browser                              Browser
    |                                    |
    v                                    v
+---------------+                 +---------------+
|   dev-ui      |                 |  dev-admin    |      <- both HTTPS automatically,
| (Amplify      |                 | (Amplify      |         AWS-managed certs, free
|  Hosting)     |                 |  Hosting)     |
+-------+-------+                 +-------+-------+
        |  /api/* rewritten               |  /api/* rewritten
        |  server-side to ----------------+  server-side to
        v  the backend ALB                   the backend ALB
+--------------------------------------------------+
|     Application Load Balancer (HTTP, port 80)     |
+----------------------+-----------------------------+
                        v
              +-------------------+
              |  ECS Fargate task |
              |  (FastAPI backend)|
              +---------+---------+
                        |
                        |  verifies JWT signature + claims
                        v
              +-------------------+        +--------------------+
              |   AWS Cognito     |         |     DynamoDB       |
              |   User Pool       |         | aws-advance-arch-  |
              | (+ Admins group)  |         |   items table      |
              +-------------------+         +--------------------+
```

The backend calls both Cognito (to verify who's calling) and DynamoDB (to
read/write that user's items) on every authenticated request.

| Piece | Why it's here |
|---|---|
| **dev-ui / dev-admin (Amplify Hosting)** | Two separate static sites, each with its own Cognito App Client, deployed with zero server management and automatic HTTPS. |
| **Amplify rewrite rule (`/api/*`)** | Lets each HTTPS frontend call the HTTP-only backend without the browser blocking it as "mixed content" — the proxying happens server-side at Amplify's edge, so the browser never touches the backend's HTTP URL directly. No custom domain or certificate needed for this. |
| **ECS Fargate backend** | Runs the FastAPI container that verifies Cognito JWTs and serves the actual API. |
| **Application Load Balancer** | One stable entry point for the backend; also what Amplify's rewrite rule targets. |
| **Cognito User Pool** | Handles sign-up, sign-in, and issues the JWT access tokens both frontends use to call the backend. One pool, shared by both apps. |
| **Cognito "Admins" group** | The authorization boundary — `dev-admin`'s API calls only succeed if the signed-in user is in this group; `dev-ui` users normally aren't. |
| **Two App Clients** | Cognito lets you register multiple "clients" (think: separate apps) against the same User Pool. `dev-ui` and `dev-admin` each get their own, so you can see/revoke their access independently later if needed. |
| **DynamoDB table (on-demand)** | Stores each user's submitted items, partitioned by their Cognito `sub` so one user's data is naturally isolated from another's — no fixed/hourly cost, bills purely per request. |
| **Backend task role** | A separate IAM role (distinct from the execution role) that grants the *application code* permission to call DynamoDB — see Step 3 for why these two roles are different things. |

---

## 2. Glossary — every AWS concept used here

**Cognito User Pool** — a managed user directory: sign-up, sign-in, password resets, email verification, and JWT issuance, all handled by AWS. You don't write any of that logic yourself.

**App Client** — a registered "application" allowed to authenticate against a User Pool. Each app client gets its own ID (not a secret, safe to embed in frontend code) and can have different allowed auth flows. One User Pool can have many app clients — here, one for `dev-ui`, one for `dev-admin`.

**Cognito Group** — a named label you can put users into (e.g., "Admins"). Shows up as a `cognito:groups` claim inside the JWT access token. This project's backend checks for that claim to decide who can call admin-only endpoints — Cognito doesn't enforce this itself, your backend code does (which is exactly what `backend/main.py`'s `require_admin` function does).

**JWT (JSON Web Token) / Access Token** — what the user gets after signing in: a signed, tamper-proof blob containing who they are and what groups they're in. The backend verifies its signature using Cognito's public keys (JWKS) rather than trusting it blindly.

**JWKS (JSON Web Key Set)** — the public keys Cognito publishes at a well-known URL, used to verify that a JWT was really signed by Cognito and hasn't been tampered with.

**DynamoDB** — AWS's managed NoSQL database. No servers to provision, no schema migrations — you define a table's key structure once (here: partition key `user_sub`, sort key `item_id`) and it scales automatically. **On-demand billing mode** (used here) charges purely per request, with no capacity planning and no fixed fee — the simplest mode to reason about for a short test, though provisioned-capacity mode can be cheaper at steady, predictable, high-volume traffic.

**Partition key / Sort key** — DynamoDB's two-part primary key. Items sharing the same partition key (here, all of one user's items) are stored together and can be fetched efficiently with a `Query` — much cheaper and faster than scanning the whole table, which is why `backend/db.py`'s `list_items` uses `Query` but its admin-only `count_all_items` (a full-table count across every user) uses the pricier `Scan` instead, deliberately, since that one genuinely needs to see every item.

**AWS Amplify Hosting** — a static-site/web-app hosting service with built-in CI/CD: point it at a GitHub repo (and a subdirectory, for a monorepo like this one), and it rebuilds and redeploys automatically on every push, with free automatic HTTPS. This is doing for the frontends what Cloud Build did automatically for Cloud Run in the earlier GCP project — except here it's Amplify's own built-in system, not something you wire up separately.

**Amplify "Rewrites and redirects"** — a proxy/routing rule you configure per Amplify app. Used here to forward `/api/*` requests to the backend ALB — important because it keeps the HTTPS frontend from ever directly calling the plain-HTTP backend in the browser (see Section 1).

**ECS, Fargate, Task Definition, Task, Service, Cluster, ALB, Target Group, Listener, Execution Role** — all the same concepts from the earlier `gcp-traditional-arch` project's AWS guide. If you haven't seen those yet, the short version: Fargate runs your container without managing servers; a task definition describes that container; a service keeps a specified number of tasks running and health-checked; an ALB is the load balancer in front of it. See that project's `AWS_DEPLOYMENT_GUIDE.md` for the fuller explanations if needed — this guide focuses on what's new here (Cognito + Amplify) and keeps the ECS/ALB steps brief.

---

## 3. Prerequisites

- An AWS account with billing enabled, and an IAM user with console + programmatic access (same as the earlier AWS test project).
- The code already pushed to GitHub: `https://github.com/Muhammad-Ali500/aws-advance-arch` (already done).
- A dedicated IAM user for GitHub Actions CI/CD (only needed for the backend — Amplify's CI/CD doesn't need this, it connects directly via OAuth/Console).

---

## 4. Cost summary

Full breakdown in `cost.txt`. Short version: **~$0.10–$0.15 for a 3-hour test**, almost entirely the ALB's hourly charge — Amplify Hosting, Cognito, and DynamoDB (on-demand mode) all round to $0.00 at this scale, and there's only one Fargate task (the backend) since both frontends run on Amplify instead.

---

## 5. Where things stand already

- All code (both frontends + backend) is written, and **tested locally end-to-end** against `cognito-local` (a real Cognito emulator) and AWS's own official `amazon/dynamodb-local` image — the full auth/authorization matrix was verified with curl before anything was pushed: public access works, missing/invalid tokens are rejected, a regular user can call `/api/me` but gets `403` on `/api/admin/stats`, and an admin user succeeds on both. Both frontend builds were confirmed to each bake in only their own Cognito App Client ID.
- **DynamoDB integration also tested end-to-end**: a user's created items are only visible to that same user (`GET /api/items` correctly isolates by `user_sub`), while the admin stats endpoint correctly counts items across *all* users via a full-table scan — confirmed with real data from two different test accounts before anything was pushed.
- Pushed to GitHub already, including the backend's GitHub Actions workflow and both frontends' `amplify.yml` build specs.
- **Nothing exists on AWS yet** — this guide starts from zero, and per your explicit instruction, nothing will be created on AWS except by you, following these steps yourself.

---

## 6. Step 1 — Create the Cognito User Pool

1. Console → **Cognito** → **Create user pool**.
2. Sign-in options: check **Email** (so users sign in/up with an email address — matches what the frontend code expects).
3. Password policy: leave defaults, or relax for testing (Cognito's defaults are reasonable for a real deployment).
4. MFA: **No MFA** (keep this simple for a test).
5. On the "Configure sign-up experience" page, leave self-registration enabled.
6. User pool name: `aws-advance-arch-pool`.
7. Create the pool. **Copy the User Pool ID** (looks like `us-east-1_XXXXXXX`) — you'll need it repeatedly below.
8. Inside the pool → **App integration** tab → **App clients** → **Create app client**:
   - Name: `dev-ui`. App type: **Public client** (no client secret — this runs in a browser, a secret couldn't be kept safe there anyway).
   - Authentication flows: check **ALLOW_USER_PASSWORD_AUTH** and **ALLOW_REFRESH_TOKEN_AUTH**.
   - Create. **Copy this App Client ID.**
9. Repeat for a second app client named `dev-admin`, same settings. **Copy its App Client ID too.**
10. Still in **App integration** → scroll to **Groups** (or find "Groups" in the left sub-menu of the pool) → **Create group**:
    - Name: `Admins`. Leave the rest default. Create.
11. Create your two test accounts (or use the self-service sign-up flow from `dev-ui` once it's deployed in Step 11, then come back here to promote one to admin):
    - Users tab → **Create user** → fill in an email + temporary password → create.
    - Repeat for a second user you want to be the admin.
    - For the admin one: open that user → **Group memberships** → **Add to group** → select `Admins`.

> **Note the real User Pool ID and BOTH App Client IDs somewhere handy** - every later step needs them.

---

## 7. Step 2 — Create the VPC, subnets, and security groups

(Same pattern as the earlier AWS test project — condensed here since it's not new.)

1. VPC → **Create VPC** → choose **"VPC and more"**.
2. Name: `aws-advance-arch-vpc`. 2 Availability Zones, 2 public subnets, 0 private subnets, **NAT gateways: None** (keeps cost at $0 for networking, same reasoning as before — Fargate tasks get public IPs directly instead).
3. Create.
4. Security Groups → **Create security group**:
   - `aws-advance-arch-alb-sg`: inbound HTTP (80) from `0.0.0.0/0`.
   - `aws-advance-arch-tasks-sg`: inbound port `8080` from `aws-advance-arch-alb-sg` only.

---

## 8. Step 3 — Create the ECR repository, DynamoDB table, and IAM roles

1. ECR → **Create repository** → name: `aws-advance-arch-backend`. Create.
2. IAM → **Roles** → **Create role** → AWS service → Elastic Container Service → **Elastic Container Service Task** → attach `AmazonECSTaskExecutionRolePolicy` → name it exactly `ecsTaskExecutionRole` (matches the task definition template). Skip this if you already created this exact role for an earlier project — it's reusable across any ECS task in the account.
3. **DynamoDB → Create table**:
   - Table name: `aws-advance-arch-items`.
   - Partition key: `user_sub` (String). Sort key: `item_id` (String) — matches `backend/db.py` exactly.
   - Table settings: **Default settings** (this already means on-demand/"Pay-per-request" capacity mode — no capacity planning needed, and no fixed hourly charge either way).
   - Create.
4. **Create the backend's task role** (separate from the execution role in step 2 — this one is what the *application code* uses to call DynamoDB, not what ECS itself uses to pull the image/write logs):
   - IAM → **Roles** → **Create role** → AWS service → Elastic Container Service → **Elastic Container Service Task**.
   - Attach a policy granting DynamoDB access to just this table — **Create policy** → JSON:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [{
         "Effect": "Allow",
         "Action": ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan"],
         "Resource": "arn:aws:dynamodb:<REGION>:<AWS_ACCOUNT_ID>:table/aws-advance-arch-items"
       }]
     }
     ```
   - Name the role exactly `aws-advance-arch-backend-task-role` (matches the task definition template).

---

## 9. Step 4 — Wire up GitHub Actions for the backend's CI/CD

1. IAM → **Users** → **Create user** → name `github-actions-deployer-advance` (or reuse one from an earlier project if you still have it) → attach permissions for ECR push + ECS deploy (or `AdministratorAccess` for a quick test).
2. That user → **Security credentials** → **Create access key** → "Application running outside AWS" → copy both values.
3. GitHub repo → **Settings → Secrets and variables → Actions** → add:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

---

## 10. Step 5 — Create the ECS cluster, task definition, and service behind an ALB

1. ECS → **Clusters** → **Create cluster** → name `aws-advance-arch-cluster` → AWS Fargate → Create.
2. Open `aws/backend-task-def.json` locally and replace every placeholder (`<AWS_ACCOUNT_ID>`, `<ACCOUNT_ID>`, `<REGION>`, `<USER_POOL_ID>`, `<DEV_UI_APP_CLIENT_ID>`, `<DEV_ADMIN_APP_CLIENT_ID>`) with your real values from Step 1 and your account. Commit and push that change (this is a config file, not a secret — app client IDs aren't sensitive).
3. ECS → **Task definitions → Create new task definition → Create new task definition with JSON** → paste the filled-in JSON → Create.
4. **EC2 → Load Balancers → Create load balancer → Application Load Balancer**:
   - Name: `aws-advance-arch-alb`. Internet-facing. Your VPC + both public subnets. Security group: `aws-advance-arch-alb-sg`.
   - Listener: HTTP, port 80.
   - Default action → create a new target group: `backend-tg`, type **IP**, protocol/port HTTP/8080, health check path `/api/public`.
   - Create.
5. ECS → cluster → **Create service**:
   - Task definition: `aws-advance-arch-backend`. Service name: `backend`. Desired tasks: 1.
   - Networking: your VPC, both public subnets, security group `aws-advance-arch-tasks-sg`, **Public IP: ON** (no NAT Gateway needed).
   - Load balancing: Application Load Balancer → `aws-advance-arch-alb` → container `backend:8080` → existing target group `backend-tg`.
   - Create. Wait for 1/1 running tasks and a healthy target group.
6. **Copy the ALB's DNS name** (EC2 → Load Balancers → your ALB → "DNS name" field) — you need it for both Amplify rewrite rules below.
7. Push any commit touching `backend/` to `main` from now on and GitHub Actions redeploys it automatically (already wired up).

---

## 11. Step 6 — Deploy dev-ui to Amplify Hosting

1. Console → **Amplify** → **Create new app** → **Deploy an app** → connect your GitHub account → select the `aws-advance-arch` repo, branch `main`.
2. **App name**: `dev-ui`. Since this is a monorepo, find **"Monorepo"** / **"App root directory"** setting and set it to `dev-ui` — this tells Amplify to treat that subfolder as its own app, using its own `amplify.yml`.
3. Amplify should auto-detect the build settings from `dev-ui/amplify.yml` — confirm they look right (npm ci, npm run build, artifacts from `dist`).
4. **Environment variables** (App settings → Environment variables) — add:
   - `VITE_USER_POOL_ID` = your real User Pool ID
   - `VITE_USER_POOL_CLIENT_ID` = the **dev-ui** App Client ID (not dev-admin's)
   - Leave `VITE_COGNITO_ENDPOINT` unset entirely (only used for local testing against cognito-local — Vite/the code falls back to real AWS Cognito's regional endpoint when it's absent).
5. Save and deploy. Wait for the build to go green.
6. **Add the API rewrite rule**: App settings → **Rewrites and redirects** → add a rule:
   - Source address: `/api/<*>`
   - Target address: `http://<your-ALB-DNS-name>/api/<*>`
   - Type: **Rewrite (200)** (not a redirect — a rewrite proxies server-side; a redirect would send the browser's own request to the HTTP URL directly, which defeats the whole point).
7. Save.

---

## 12. Step 7 — Deploy dev-admin to Amplify Hosting

Repeat Step 6, with these differences:
- App root directory: `dev-admin`
- Environment variable `VITE_USER_POOL_CLIENT_ID` = the **dev-admin** App Client ID
- Same rewrite rule (`/api/<*>` → your ALB's DNS name) — both apps proxy to the same backend.

---

## 13. Step 8 — Test it end-to-end

1. Open dev-ui's Amplify URL (shown on the app's overview page, looks like `https://main.xxxxx.amplifyapp.com`).
2. Sign up a new account (or sign in with one you created manually in Step 1), confirm via the email code Cognito actually sends now (real AWS Cognito, unlike local testing, sends real email).
3. Click the button that calls `/api/me` — should show your user info, including an empty `groups` list (unless you added this user to Admins).
4. Open dev-admin's Amplify URL, sign in as the user you added to the `Admins` group in Step 1.
5. Call `/api/admin/stats` — should succeed. Try signing into dev-admin as a non-admin user instead — should get a 403, proving the authorization boundary works in the real deployment the same way it did in local testing.

---

## 14. Step 9 — Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Amplify build fails at `npm ci` | Root directory not set to `dev-ui`/`dev-admin`, so it's looking in the repo root for `package.json` | App settings → confirm the monorepo root directory setting |
| Frontend loads but API calls fail with a network/CORS-looking error | Rewrite rule missing or pointing at the wrong ALB DNS name | App settings → Rewrites and redirects → confirm the rule and target host |
| `/api/me` returns 401 even when signed in | Wrong `VITE_USER_POOL_CLIENT_ID` for that app, or User Pool ID mismatch | Double-check the app's environment variables match the right App Client from Step 1 |
| `/api/admin/stats` always 403, even for the admin test user | User not actually in the `Admins` group, or signed in via the wrong app client | Cognito console → Users → confirm group membership; confirm you're testing via dev-admin, not dev-ui |
| ECS task won't reach healthy in the target group | Health check path wrong, or security group blocking ALB→task traffic | Confirm target group health check path is `/api/public`; confirm `aws-advance-arch-tasks-sg` allows inbound 8080 from `aws-advance-arch-alb-sg` |
| GitHub Actions fails at ECR push | ECR repo not created yet, or IAM user lacks permission | Confirm Step 3 was completed and the secret values are correct |
| `/api/items` returns 500, or logs show an AWS auth/permission error | Task role missing or not attached, or DynamoDB table name mismatch | Confirm the task definition's `taskRoleArn` is set and the role has the DynamoDB policy from Step 3; confirm `DYNAMODB_TABLE_NAME` matches the real table name exactly |
| A user sees another user's items | Should never happen if `backend/db.py` is unmodified (it queries by `user_sub` from the verified JWT, not anything client-supplied) | If you've changed the code, double check the partition key is still derived from `claims["sub"]`, never from client input |

---

## 15. Step 10 — Teardown (delete everything)

> **⚠️ The ALB is the one resource billing by the hour** — delete it first if you're tearing down in a hurry, then clean up the rest.

1. ECS → service → set desired count to 0, then delete the service; delete the cluster.
2. EC2 → Load Balancers → delete `aws-advance-arch-alb`; Target Groups → delete `backend-tg`.
3. ECR → delete the `aws-advance-arch-backend` repository.
4. Amplify → delete both the `dev-ui` and `dev-admin` apps (Console → app → App settings → General → Delete app).
5. Cognito → delete the `aws-advance-arch-pool` User Pool (this also removes its app clients, groups, and users).
6. **DynamoDB → delete the `aws-advance-arch-items` table** (this permanently deletes all stored items too — expected and fine for a test).
7. VPC → delete `aws-advance-arch-vpc` (cleans up its subnets/route tables/internet gateway together).
8. IAM → delete the `github-actions-deployer-advance` user and its access key, the `aws-advance-arch-backend-task-role` and its custom DynamoDB policy, and the custom policy if you made one (keep `ecsTaskExecutionRole` — it's a standard, reusable, free role).
9. Double-check: ECS shows no services, EC2 Load Balancers is empty, Amplify shows no apps, and DynamoDB shows no tables — those are the resources that mattered for cost/cleanliness.

---

## 16. Appendix: how a request flows through this system

1. A user opens `dev-ui`'s Amplify URL and signs in. `amazon-cognito-identity-js` runs the real SRP-based Cognito auth protocol directly against AWS Cognito (no backend involved in login itself) and gets back a JWT access token, stored in the browser.
2. The user clicks a button that calls `/api/me`. The browser's `fetch` goes to `dev-ui`'s own Amplify domain (`https://main.xxxxx.amplifyapp.com/api/me`) — still HTTPS, still the same origin, no mixed content.
3. Amplify's edge sees the `/api/*` rewrite rule and forwards the request **server-side** to `http://<alb-dns-name>/api/me`, carrying the `Authorization: Bearer <token>` header through unchanged.
4. The ALB routes it to a healthy backend task via `backend-tg`.
5. The backend fetches Cognito's JWKS (cached for an hour), verifies the token's signature and `iss`/`token_use`/`client_id` claims, and returns the decoded user info.
6. The response travels back through the ALB → Amplify's edge → the browser, which only ever saw its own HTTPS domain throughout.

`dev-admin` works identically, except its calls to `/api/admin/stats` additionally require the token's `cognito:groups` claim to include `Admins` — enforced entirely in the backend's own code (`require_admin` in `backend/main.py`), not by anything Cognito or the ALB does automatically.

When a user calls `POST /api/items` or `GET /api/items`, the backend uses the verified token's `sub` claim (never anything the client sends directly) as the DynamoDB partition key — this is what makes one user's items structurally invisible to another user's queries, rather than relying on application logic alone to filter them out after the fact.
