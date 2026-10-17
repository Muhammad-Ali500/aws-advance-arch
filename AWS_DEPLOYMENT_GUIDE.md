# aws-advance-arch: Complete Click-by-Click Deployment (3-hour practice run)

Practice run for the real Slotta staging deployment. Same AWS services and settings, basic app.
Everything is done **by you in the AWS console**. Nothing here is automated.

- **Region:** `US East (N. Virginia) us-east-1`. Check the region selector (top right) before **every** step.
- **Sign in:** IAM Identity Center access portal → your account → *AdministratorAccess*. Never the root user.
- **Repo:** `https://github.com/Muhammad-Ali500/aws-advance-arch`. **Commit and push the latest local changes first**: AWS builds from GitHub, not from your PC.
- **Cost:** ~$0.45–0.65 for 3 hours (details in `cost.txt`).
- **Track A** (default in this guide): no domain, HTTP ALB, frontends proxy the API. **Track B** (optional boxes 🅱): your own domain + HTTPS, exactly like Slotta.

---

## Time plan

| Part | Steps | Time (first time) | Billing clock |
|---|---|---|---|
| **Part 1: free resources** | Budget, DynamoDB, S3, KMS, Secrets, SQS, Cognito, ECR, logs, IAM, GitHub connection, first image build | 45–60 min | ~$0 (do this the day before if you like) |
| **Part 2: network + backend** | VPC + NAT, security groups, target group, ALB, ECS cluster/task/service | 30–40 min | **starts here** (NAT, ALB) |
| **Part 3: frontends + pipeline** | 2 Amplify apps, CodePipeline | 25–35 min | running |
| **Part 4: test** | checklist | 15–20 min | running |
| **Part 5: teardown** | delete everything | 20–25 min | stops when NAT + ALB are gone |
| **Total** | | **~2.5–3 h**; the paid window is about 1.5–2 h | |

🅱 Track B adds 20–40 min (DNS delegation + certificate validation). Start Phase B1 at the very beginning so the certificate validates while you work.

Keep a notepad open: you'll copy about 12 values (marked 📋) between steps.

---

# PART 1: Free / near-free resources

## 1. Budget alert (2 min)
1. Top search bar → type **Billing** → **Billing and Cost Management**.
2. Left menu **Budgets** → **Create budget**.
3. **Use a template (simplified)** → **Monthly cost budget**.
4. Budget name `practice-budget` · Amount `5` · Email: your email → **Create budget**.

## 🅱 B1. Domain + certificate (Track B only; start now, it validates in the background)
1. Search **Route 53** → **Hosted zones** → **Create hosted zone** → Domain name e.g. `practice.yourdomain.com` → **Public hosted zone** → **Create hosted zone**.
2. Open the zone → copy the 4 **NS** values → at the place that hosts `yourdomain.com`, create an **NS** record named `practice` with those 4 values.
3. Search **Certificate Manager** → **Request** → **Request a public certificate** → **Next**.
4. Domain names: `practice.yourdomain.com` **and** `*.practice.yourdomain.com` → DNS validation → **Request**.
5. Open the certificate → **Create records in Route 53** → **Create records**. Status turns **Issued** in 5–30 min. 📋 certificate ARN.

## 2. DynamoDB table (2 min)
1. Search **DynamoDB** → left **Tables** → **Create table**.
2. Table name: `aws-advance-arch-items`
3. Partition key: `user_sub` (String) · Sort key: `item_id` (String)
4. Table settings: **Default settings** (on-demand capacity) → **Create table**. Wait for **Active**.

## 3. S3 bucket (2 min)
1. Search **S3** → **Create bucket**.
2. Bucket type **General purpose** · Bucket name `aws-advance-arch-logo-<yourname>-<random digits>` (must be globally unique).
3. Leave **Block all public access** ✔ ON and the other defaults → **Create bucket**. 📋 bucket name.

## 4. KMS key (3 min)
1. Search **Key Management Service** → **Customer managed keys** → **Create key**.
2. Key type **Symmetric** · Key usage **Encrypt and decrypt** → **Next**.
3. Alias `aws-advance-arch-tokens` → **Next**.
4. Key administrators: tick your `AWSReservedSSO_AdministratorAccess_...` role → **Next**.
5. Key users: tick nothing (the task role gets access through IAM) → **Next** → **Finish**.
6. Open the key → 📋 **ARN**.

## 5. Secrets Manager (2 min)
1. Search **Secrets Manager** → **Store a new secret**.
2. Secret type **Other type of secret** → tab **Plaintext** → replace everything with `{"api_key":"practice"}` → **Next**.
3. Secret name: **`slotta-dummy/app`** (exactly) → **Next** → rotation off → **Next** → **Store**.

## 6. SQS queues (3 min)
1. Search **SQS** → **Create queue** → **Standard** → Name `waitlist-events-dlq` → **Create queue**.
2. Back to **Queues** → **Create queue** → **Standard** → Name `waitlist-events`.
3. Scroll to **Dead-letter queue** → **Enabled** → choose `waitlist-events-dlq` → Maximum receives `5` → **Create queue**.
4. 📋 the **URL** of `waitlist-events` (e.g. `https://sqs.us-east-1.amazonaws.com/123456789012/waitlist-events`).

## 7. Cognito (8 min), same settings as Slotta
1. Search **Cognito** → **Create user pool**.
2. **Define your application**: Application type **Single-page application (SPA)** · Name `aws-advance-arch-web`.
3. **Configure options**: Options for sign-in identifiers: ✔ **Email** only · **Self-registration: off (unticked)** · Required attributes: email.
4. Return URL: leave empty → **Create user directory**. On the next page click **Go to overview**.
5. 📋 **User pool ID** (e.g. `us-east-1_AbC123`).
6. Left menu **App clients** → click `aws-advance-arch-web` → 📋 **Client ID** → **Edit** (App client information):
   - Authentication flows: ✔ `ALLOW_ADMIN_USER_PASSWORD_AUTH` ✔ `ALLOW_REFRESH_TOKEN_AUTH` ✔ `ALLOW_USER_SRP_AUTH` (untick others) → **Save changes**.
7. Left menu **Groups** → **Create group** → `SUPER_ADMIN` → **Create group**. Repeat for `ADMIN`.
8. Left menu **Users** → **Create user**:
   - Invitation: **Don't send an invitation** · Email `admin@example.com` (or yours) · ✔ Mark email address as verified · Password: **Set a password** `TestPass123!` → **Create user**.
   - Open the user → **Add user to group** → `ADMIN` → **Add**.
   - Create a second user `user@example.com` the same way, with **no group**.
9. **Make the passwords permanent.** Console-created users must change their password at first login, and the dummy login doesn't handle that step. Open **CloudShell** (the `>_` icon in the top bar), then run:
   ```bash
   POOL=us-east-1_AbC123   # your pool id
   aws cognito-idp admin-set-user-password --user-pool-id $POOL --username admin@example.com --password 'TestPass123!' --permanent
   aws cognito-idp admin-set-user-password --user-pool-id $POOL --username user@example.com  --password 'TestPass123!' --permanent
   ```
   Users list → both show **Confirmed**.

## 8. ECR repository (2 min)
1. Search **Elastic Container Registry** → **Private registry → Repositories** → **Create repository**.
2. Name `aws-advance-arch-backend` · Image tag mutability **Mutable** → **Create**.
3. 📋 the repository URI.

## 9. CloudWatch log group (1 min)
Search **CloudWatch** → **Logs → Log groups** → **Create log group** → `/ecs/aws-advance-arch-backend` → Retention **1 week** → **Create**.

## 10. IAM roles (8 min)
**Execution role** (lets ECS pull the image and write logs):
1. Search **IAM** → **Roles** → **Create role** → Trusted entity **AWS service** → Service **Elastic Container Service** → Use case **Elastic Container Service Task** → **Next**.
2. Search and tick `AmazonECSTaskExecutionRolePolicy` → **Next** → Role name `aws-advance-arch-ecs-execution-role` → **Create role**.

**Task role** (what the app may do):
1. **Create role** → same trusted entity / use case → **Next** → tick nothing → **Next** → name `aws-advance-arch-backend-task-role` → **Create role**.
2. Open it → **Add permissions** → **Create inline policy** → **JSON** tab.
3. Paste `aws/backend-task-role-policy.json` and replace `<AWS_ACCOUNT_ID>`, `<USER_POOL_ID>`, `<LOGO_BUCKET_NAME>`, `<KMS_KEY_ARN>` → **Next** → name `app-permissions` → **Create policy**.

(Your account ID is the 12 digits in the top-right menu.)

## 11. GitHub connection + first image build (10–12 min, no Docker needed on your PC)
1. Search **CodePipeline** → left **Settings → Connections** → **Create connection** → **GitHub** → name `github` → **Connect to GitHub** → **Install a new app** → choose your account → allow the `aws-advance-arch` repo → **Connect**. Status = **Available**.
2. Search **CodeBuild** → **Create project**:
   - Project name `aws-advance-arch-backend-build`
   - Source provider **GitHub** → **Custom source credential / GitHub App** using the `github` connection → Repository: `aws-advance-arch` → leave webhook unticked
   - Environment: **Managed image** · Compute **EC2** · OS **Amazon Linux** · Runtime **Standard** · Image: latest · ✔ **Privileged** (needed for Docker builds) · Service role: **New service role**
   - **Additional configuration → Environment variables**: `AWS_ACCOUNT_ID` = your 12 digits · `ECR_REPO` = `aws-advance-arch-backend` · `CONTAINER_NAME` = `backend`
   - Buildspec: **Use a buildspec file** (it finds `buildspec.yml` in the repo root)
   - Artifacts: **No artifacts** · Logs: CloudWatch ✔ → **Create build project**
3. Give the build role ECR push rights: **IAM → Roles** → open `codebuild-aws-advance-arch-backend-build-service-role` → **Add permissions → Attach policies** → `AmazonEC2ContainerRegistryPowerUser` → **Add permissions**.
4. Back in CodeBuild → the project → **Start build** → wait for **Succeeded** (~3 min).
5. ECR → your repo → you should see tags `v1`, a commit hash, and **`latest`**.

✅ **End of Part 1. Nothing so far bills by the hour.**

---

# PART 2: Network + backend (the billing clock starts here)

## 12. VPC (5 min + ~3 min NAT provisioning)
1. Search **VPC** → **Create VPC** → choose **VPC and more**.
2. Name tag auto-generation: `aws-advance-arch` · IPv4 CIDR `10.0.0.0/16`.
3. Number of AZs **2** · Public subnets **2** · Private subnets **2**.
4. NAT gateways: **In 1 AZ** · VPC endpoints: **S3 Gateway**.
5. DNS hostnames ✔ · DNS resolution ✔ → **Create VPC** → wait until every line is green → **View VPC**.
6. Add the DynamoDB endpoint: left **Endpoints** → **Create endpoint** → Name `ddb` · **AWS services** → search `dynamodb` → select `com.amazonaws.us-east-1.dynamodb` (**Gateway**) → VPC `aws-advance-arch-vpc` → tick the two **private** route tables (names contain `rtb-private`) → **Create endpoint**.

## 13. Security groups (4 min)
VPC → **Security groups** → **Create security group**:
1. Name `aws-advance-arch-alb-sg` · Description `alb` · VPC `aws-advance-arch-vpc` · **Inbound rules → Add rule**: Type **HTTP**, Source **Anywhere-IPv4** (🅱 add another rule: **HTTPS**, Anywhere-IPv4) → **Create security group**.
2. **Create security group** → Name `aws-advance-arch-tasks-sg` · Description `tasks` · same VPC · Inbound: Type **Custom TCP**, Port **3000**, Source: **Custom** → pick `aws-advance-arch-alb-sg` from the list → **Create security group**.

## 14. Target group (3 min)
1. Search **EC2** → left **Load Balancing → Target Groups** → **Create target group**.
2. Target type **IP addresses** · Name `aws-advance-arch-tg` · Protocol **HTTP** · Port **3000** · VPC `aws-advance-arch-vpc`.
3. Health checks: path **`/health`** → expand **Advanced**: Healthy threshold 2 · Interval 15 → **Next**.
4. Don't register any targets → **Create target group**.

## 15. Load balancer (4 min + ~3 min provisioning)
1. EC2 → **Load Balancers** → **Create load balancer** → **Application Load Balancer** → **Create**.
2. Name `aws-advance-arch-alb` · **Internet-facing** · IPv4.
3. Network mapping: VPC `aws-advance-arch-vpc` → tick both AZs → choose the **public** subnet in each.
4. Security groups: remove `default`, select `aws-advance-arch-alb-sg`.
5. Listeners: **HTTP : 80** → Default action **Forward to** `aws-advance-arch-tg`.
   🅱 Track B: **Add listener** **HTTPS : 443** → forward to `aws-advance-arch-tg` → certificate from ACM. After creation, edit the HTTP:80 listener → **Redirect to URL** → HTTPS 443, 301.
6. **Create load balancer**. 📋 **DNS name** (e.g. `aws-advance-arch-alb-123.us-east-1.elb.amazonaws.com`).
7. Open the ALB → **Attributes** tab → **Edit** → **Connection idle timeout = 120** seconds → **Save changes**.
8. 🅱 Route 53 → your zone → **Create record** → name `api` → type **A** → **Alias** ON → *Alias to Application and Classic Load Balancer* → us-east-1 → the ALB → **Create records**.

## 16. ECS cluster (2 min)
Search **Elastic Container Service** → **Clusters** → **Create cluster** → name `aws-advance-arch-cluster` → Infrastructure **AWS Fargate (serverless)** → Monitoring: **Container Insights** on → **Create**.

## 17. Task definition (5 min)
1. Open `aws/backend-task-def.json` on your PC and replace:

| Placeholder | Value |
|---|---|
| `<AWS_ACCOUNT_ID>` | your 12 digits (appears several times) |
| `<USER_POOL_ID>` / `<APP_CLIENT_ID>` | from step 7 |
| `ALLOWED_ORIGINS` value | Track A: `*` · 🅱 the Amplify/custom domains, comma-separated |
| `<LOGO_BUCKET_NAME>` | step 3 |
| SQS URL | step 6 |
| `<KMS_KEY_ARN>` | step 4 |

2. ECS → **Task definitions** → **Create new task definition** ▾ → **Create new task definition with JSON** → delete the sample → paste your filled JSON → **Create**.

## 18. Service (5 min + 3–5 min to become healthy)
1. ECS → **Clusters** → `aws-advance-arch-cluster` → **Services** tab → **Create**.
2. **Compute configuration**: Compute options **Launch type** → **FARGATE** → Platform **LATEST**.
3. **Deployment configuration**: Application type **Service** · Family `aws-advance-arch-backend` (latest revision) · Service name **`backend`** · Desired tasks **1**.
   - Expand **Deployment options / failure detection**: ✔ **Use the Amazon ECS deployment circuit breaker** ✔ **Rollback on failures**.
4. **Networking**: VPC `aws-advance-arch-vpc` · Subnets: **only the two private** ones (remove the public ones) · Security group: **Use an existing** → `aws-advance-arch-tasks-sg` (remove default) · **Public IP: OFF**.
5. **Load balancing**: ✔ Use load balancing → **Application Load Balancer** → **Use an existing load balancer** `aws-advance-arch-alb` → Container to load balance `backend 3000:3000` → Listener **Use an existing listener** `80:HTTP` (🅱 `443:HTTPS`) → Target group **Use an existing target group** `aws-advance-arch-tg` → Health check grace period `90`.
6. **Create**.
7. Wait: **Services → backend → Tasks**: 1 **Running** · **EC2 → Target groups → aws-advance-arch-tg → Targets**: 1 **healthy**.
8. Browser: `http://<ALB DNS name>/health` → `{"status":"ok"}` (🅱 `https://api.practice.yourdomain.com/health`).

If the task keeps stopping: open the stopped task → **Logs** tab / *Stopped reason*. Usual causes: a wrong placeholder in the task definition, or a Secrets Manager / IAM denial (the app reads the secret at boot).

---

# PART 3: Frontends + pipeline

## 19. Amplify: Admin portal (`dev-admin`, static) (8–10 min)
1. Search **Amplify** → **Create new app** → **GitHub** → **Next** → authorise Amplify → repository `aws-advance-arch` · branch `main` → ✔ **My app is a monorepo** → Monorepo root directory **`dev-admin`** → **Next**.
2. App name `dev-admin`. Build settings: auto-detected from the root `amplify.yml` (frontend = `dist`).
3. **Advanced settings → Environment variables**:
   - Track A: add none.
   - 🅱 `VITE_API_BASE_URL` = `https://api.practice.yourdomain.com` (and add that origin to `connect-src` in `amplify.yml` → commit → push).
4. **Next** → **Save and deploy** → wait for Deploy ✔ (~3 min). 📋 the domain `https://main.xxxx.amplifyapp.com`.
5. Track A only: left **Hosting → Rewrites and redirects** → **Manage redirects** → **Add rewrite** twice:

| Source address | Target address | Type |
|---|---|---|
| `/api/<*>` | `http://<ALB DNS name>/api/<*>` | Rewrite (200) |
| `/auth/<*>` | `http://<ALB DNS name>/auth/<*>` | Rewrite (200) |

   → **Save**.
6. 🅱 **Hosting → Custom domains → Add domain** → choose your Route 53 zone → subdomain `admin` → branch `main` → **Add domain**.

## 20. Amplify: Frontend (`dev-ui`, Next.js SSR) (10–12 min)
1. Amplify → **Create new app** → GitHub → same repo, branch `main` → ✔ monorepo → root directory **`dev-ui`** → **Next**.
2. Build settings must show framework **Next.js - SSR**. If it says static/Web, stop: the root directory is wrong.
3. **Service role**: **Create and use a new service role**.
4. **Environment variables** (set them **before** the first build; they're read at build time):
   - Track A: `API_PROXY_TARGET` = `http://<ALB DNS name>`
   - 🅱 `NEXT_PUBLIC_API_BASE_URL` = `https://api.practice.yourdomain.com`
5. **Save and deploy** (~5–7 min). 📋 domain.
6. 🅱 **Custom domains → Add domain** → your zone → map root (`practice.yourdomain.com`) and **`*`** (wildcard) to `main`.

## 21. CodePipeline: backend CI/CD (6–8 min)
1. Search **CodePipeline** → **Create pipeline** → **Build custom pipeline** → **Next**.
2. Name `aws-advance-arch-backend` · Execution mode **Superseded** · Service role **New service role** → **Next**.
3. **Source**: **GitHub (via GitHub App)** → connection `github` → repo `aws-advance-arch` → branch `main` → **Next**.
4. **Build**: **Other build providers → AWS CodeBuild** → project `aws-advance-arch-backend-build` → **Next**.
5. **Test**: **Skip test stage**.
6. **Deploy**: **Amazon ECS** → cluster `aws-advance-arch-cluster` → service `backend` → Image definitions file `imagedefinitions.json` → **Next** → **Create pipeline**.
7. It runs immediately: Source ✔ → Build ✔ → Deploy ✔ (~6–8 min). ECS now runs task revision 2.

---

# PART 4: Test (15–20 min)

Open the **dev-admin** Amplify URL:
- [ ] Sign in `admin@example.com` / `TestPass123!` → "signedIn": true
- [ ] **Cognito: /api/me** → 200, groups `["ADMIN"]`
- [ ] **DynamoDB + groups: stats** → 200
- [ ] **S3**, **SQS**, **KMS**, **Secrets Manager** → each `"ok": true`
- [ ] **NAT egress** → `public_ip` = your NAT Gateway's Elastic IP (VPC → NAT gateways → compare)
- [ ] Reload, sign in as `user@example.com` → admin buttons return **403**

Open the **dev-ui** Amplify URL:
- [ ] Reload twice → `renderedAt` changes (SSR works)
- [ ] Sign in → `/api/me` → Add item → List items shows it
- [ ] DynamoDB console → `aws-advance-arch-items` → **Explore table items** → your item is there
- [ ] ECS → task → **Logs**: no errors · Target group: healthy
- [ ] SQS → `waitlist-events` → **Send and receive messages** → **Poll for messages** → the test message is there
- [ ] Optional CI/CD test: change a backend file in GitHub (e.g. the `/api/public` message) → pipeline redeploys → new message visible
- [ ] 🅱 `https://api.…/health`, `https://admin.…`, and `https://anything.practice.yourdomain.com` (wildcard) all load

---

# PART 5: Teardown (20–25 min). Hourly items first!

1. **ECS**: cluster → **Services** → `backend` → **Delete service** (✔ force delete) → wait → **Delete cluster**.
2. **EC2 → Load Balancers** → `aws-advance-arch-alb` → **Actions → Delete** → type `confirm`.
3. **EC2 → Target Groups** → `aws-advance-arch-tg` → Delete.
4. **VPC → NAT gateways** → select → **Actions → Delete NAT gateway** → wait for **Deleted** (~2 min).
5. **VPC → Elastic IPs** → select the one that was on the NAT → **Actions → Release Elastic IP addresses**. ⚠ An unreleased EIP keeps billing.
6. **VPC → Endpoints** → delete the S3 and DynamoDB endpoints → **Your VPCs** → `aws-advance-arch-vpc` → **Actions → Delete VPC** (removes subnets, route tables, IGW, security groups).
7. **CodePipeline** → delete pipeline · **CodeBuild** → delete project · **Settings → Connections** → delete `github` (optional).
8. **Amplify** → each app → **App settings → General settings** → **Delete app** (both).
9. **ECR** → repo → **Delete** (type `delete`).
10. **Cognito** → user pool → **Delete** (turn off deletion protection first if prompted).
11. **DynamoDB** → table → **Delete**.
12. **S3** → bucket → **Empty** → then **Delete**.
13. **SQS** → delete both queues.
14. **Secrets Manager** → secret → **Actions → Delete secret** → waiting period **7 days** (no charge while pending).
15. **KMS** → key → **Key actions → Schedule key deletion** → **7 days** (no charge while pending).
16. **CloudWatch** → delete log group `/ecs/aws-advance-arch-backend` (and the `/aws/codebuild/...` group).
17. **IAM → Roles** → delete `aws-advance-arch-ecs-execution-role`, `aws-advance-arch-backend-task-role`, the `codebuild-…` and `AWSCodePipelineServiceRole-…` roles, and the Amplify SSR service role.
18. 🅱 **Route 53**: delete the `api`/`admin` records → delete the hosted zone (free if deleted within 12 h) → remove the NS delegation record · **ACM**: delete the certificate.
19. **Check**: EC2 Load Balancers empty · VPC NAT gateways = Deleted · Elastic IPs empty · ECS no clusters · Amplify no apps. Next day, **Billing → Bills** should show a few cents.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| CodeBuild fails at `docker login` / push | Build role is missing `AmazonEC2ContainerRegistryPowerUser` (step 11.3), or **Privileged** isn't ticked |
| Task stops immediately | Task → *Stopped reason* + Logs. Check task definition placeholders, secret name `slotta-dummy/app`, task role policy ARNs |
| `CannotPullContainerError` | No `latest` tag in ECR (rerun step 11.4) or the task isn't in private subnets with the NAT |
| Target unhealthy | Tasks SG must allow **3000 from the ALB SG**; health path `/health`; port 3000 on the target group |
| Login says `NotAuthorizedException` | Wrong password, or the user isn't **Confirmed** (rerun the CloudShell commands, step 7.9) |
| Login says `InvalidParameterException ... ADMIN_USER_PASSWORD_AUTH` | Enable that auth flow on the app client (step 7.6) |
| `/api/me` → 401 Wrong token type or app client | `COGNITO_CLIENT_ID` in the task definition doesn't match the app client |
| Admin buttons 503 "not configured" | The env var for that service is empty in the task definition |
| S3/SQS/KMS → 500 + `AccessDenied` in logs | Placeholder left in the task role policy |
| Egress → 502 | Private route table has no route to the NAT gateway |
| dev-admin API calls return HTML / 404 | Track A rewrites missing or wrong ALB DNS name (step 19.5) |
| dev-ui API calls 404 | `API_PROXY_TARGET` was set after the build → **Redeploy this version** |
| dev-ui shows a static page / `renderedAt` never changes | App not deployed as **Next.js - SSR**: recreate with root directory `dev-ui` |
| Amplify build fails at `npm ci` | Lock file not pushed, or the monorepo root directory is wrong |
