"""
Seeds cognito-local (local Cognito emulator) with the same Cognito shape as
the real Slotta setup: ONE User Pool, ONE public App Client (no secret)
allowing ADMIN_USER_PASSWORD_AUTH (backend-driven login), groups SUPER_ADMIN
and ADMIN, and three test users.

Run this ONCE after cognito-local is up - prints the env values you need.
"""
import boto3

ENDPOINT = "http://localhost:9229"

client = boto3.client(
    "cognito-idp",
    endpoint_url=ENDPOINT,
    region_name="us-east-1",
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

print("Creating User Pool...")
pool_id = client.create_user_pool(PoolName="slotta-dummy-local")["UserPool"]["Id"]
print("  UserPoolId:", pool_id)

print("Creating App Client: slotta-dummy-web (public, no secret)...")
client_id = client.create_user_pool_client(
    UserPoolId=pool_id,
    ClientName="slotta-dummy-web",
    ExplicitAuthFlows=["ALLOW_ADMIN_USER_PASSWORD_AUTH", "ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
)["UserPoolClient"]["ClientId"]
print("  ClientId:", client_id)

for group in ("SUPER_ADMIN", "ADMIN"):
    print(f"Creating group {group}...")
    client.create_group(GroupName=group, UserPoolId=pool_id)


def create_confirmed_user(email, password, group=None):
    print(f"Creating user '{email}'...")
    client.admin_create_user(
        UserPoolId=pool_id,
        Username=email,
        UserAttributes=[{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"}],
        MessageAction="SUPPRESS",
    )
    client.admin_set_user_password(UserPoolId=pool_id, Username=email, Password=password, Permanent=True)
    if group:
        client.admin_add_user_to_group(UserPoolId=pool_id, Username=email, GroupName=group)
        print(f"  Added to {group}")


create_confirmed_user("testuser@example.com", "TestPass123!")
create_confirmed_user("testadmin@example.com", "TestPass123!", "ADMIN")
create_confirmed_user("testsuper@example.com", "TestPass123!", "SUPER_ADMIN")

print()
print("=" * 70)
print("Backend env vars (docker-compose.local.yml reads these from your shell):")
print("=" * 70)
print(f"COGNITO_USER_POOL_ID={pool_id}")
print(f"COGNITO_CLIENT_ID={client_id}")
print(f"COGNITO_ENDPOINT_URL=http://host.docker.internal:9229")
print(f"COGNITO_ISSUER=http://localhost:9229/{pool_id}")
print("  ^ cognito-local bakes 'localhost:9229' into every token's iss claim;")
print("    on real AWS the issuer is derived from the pool and needs no override.")
print(f"COGNITO_JWKS_URL=http://host.docker.internal:9229/{pool_id}/.well-known/jwks.json")
print()
print("Test users (password TestPass123!): testuser@ (no group),")
print("  testadmin@ (ADMIN), testsuper@ (SUPER_ADMIN)  - all @example.com")
