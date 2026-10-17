# aws-advance-arch

A deliberately basic practice app whose **AWS infrastructure matches the real Slotta staging setup**: two frontends on Amplify (one static, one Next.js SSR), a container backend on ECS Fargate in private subnets behind an ALB, Cognito, DynamoDB, S3, SQS, KMS, Secrets Manager, and CodePipeline.

```
dev-admin (Amplify static) --\
                              +--> ALB --> ECS Fargate backend (private subnets, :3000)
dev-ui (Amplify Next.js SSR) -/              |--> Cognito (login + JWT)
                                             |--> DynamoDB, S3, SQS, KMS, Secrets Manager
                                             '--> NAT Gateway --> internet
```

- `backend/`: FastAPI. Every endpoint tests one infra piece (see the table in the guide).
- `dev-admin/`: Vite static site with sign-in and one button per infra check.
- `dev-ui/`: Next.js 15 SSR page with sign-in and items. It shows which host served it and when it was rendered.
- `aws/`: ECS task definition + task role policy (fill in the placeholders).
- `buildspec.yml`: CodeBuild spec for CodePipeline (backend).
- `amplify.yml`: monorepo build spec for both Amplify apps.
- `_archive/`: the previous versions of files this update replaced (nothing was deleted).

**Deploy:** `AWS_DEPLOYMENT_GUIDE.md`, whose phases follow the real Slotta staging guide.
**What changed and why:** `CHANGES.md`.

**Test locally without AWS or Docker:**
```bash
pip install -r backend/requirements.txt "moto[cognitoidp]" httpx
cd local-testing && python -I test_backend_moto.py ../backend
```
