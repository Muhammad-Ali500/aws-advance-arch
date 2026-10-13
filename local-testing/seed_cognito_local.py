"""
Seeds cognito-local (local Cognito emulator) with everything needed to test
this project end-to-end: a User Pool, two App Clients (dev-ui, dev-admin),
an "Admins" group, and two test users (one regular, one admin).

Run this ONCE after cognito-local is up, before starting the other
containers - prints the IDs you need to pass as build args/env vars.
"""
import boto3

ENDPOINT = "http://localhost:9229"
REGION = "local"  # cognito-local doesn't care about the real region value

client = boto3.client(
    "cognito-idp",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

print("Creating User Pool...")
pool = client.create_user_pool(PoolName="aws-advance-arch-local")
pool_id = pool["UserPool"]["Id"]
print("  UserPoolId:", pool_id)

print("Creating App Client: dev-ui...")
ui_client = client.create_user_pool_client(
    UserPoolId=pool_id, ClientName="dev-ui", ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
)
ui_client_id = ui_client["UserPoolClient"]["ClientId"]
print("  dev-ui ClientId:", ui_client_id)

print("Creating App Client: dev-admin...")
admin_client = client.create_user_pool_client(
    UserPoolId=pool_id, ClientName="dev-admin", ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
)
admin_client_id = admin_client["UserPoolClient"]["ClientId"]
print("  dev-admin ClientId:", admin_client_id)

print("Creating 'Admins' group...")
client.create_group(GroupName="Admins", UserPoolId=pool_id)

def create_confirmed_user(username, email, password, is_admin=False):
    print(f"Creating user '{username}'...")
    client.admin_create_user(
        UserPoolId=pool_id,
        Username=username,
        UserAttributes=[{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"}],
        MessageAction="SUPPRESS",
    )
    client.admin_set_user_password(UserPoolId=pool_id, Username=username, Password=password, Permanent=True)
    if is_admin:
        client.admin_add_user_to_group(UserPoolId=pool_id, Username=username, GroupName="Admins")
        print(f"  Added '{username}' to Admins group")

create_confirmed_user("testuser@example.com", "testuser@example.com", "TestPass123!", is_admin=False)
create_confirmed_user("testadmin@example.com", "testadmin@example.com", "TestPass123!", is_admin=True)

print()
print("=" * 70)
print("Seeding complete. Use these values:")
print("=" * 70)
print(f"VITE_USER_POOL_ID={pool_id}")
print(f"VITE_USER_POOL_CLIENT_ID (dev-ui)={ui_client_id}")
print(f"VITE_USER_POOL_CLIENT_ID (dev-admin)={admin_client_id}")
print(f"VITE_COGNITO_ENDPOINT={ENDPOINT}")
print()
print("Backend env vars - NOTE the two different hostnames, this matters:")
print(f"COGNITO_ISSUER=http://localhost:9229/{pool_id}")
print("  ^ must match 'localhost' exactly - this is literally baked into")
print("    every token's 'iss' claim because the browser/seed script reach")
print("    cognito-local via localhost:9229. This is a LOCAL-TESTING-ONLY")
print("    quirk - in real AWS, the issuer and the reachable JWKS host are")
print("    always the same, so this split never comes up in production.")
print(f"COGNITO_JWKS_URL=http://host.docker.internal:9229/{pool_id}/.well-known/jwks.json")
print("  ^ must use 'host.docker.internal', not 'localhost' - the backend")
print("    runs in its OWN container, where 'localhost' means itself, not")
print("    the cognito-local container. host.docker.internal is Docker")
print("    Desktop's standard way to reach the host machine from inside")
print("    a container.")
print(f"COGNITO_APP_CLIENT_IDS={ui_client_id},{admin_client_id}")
print()
print("Test users: testuser@example.com/TestPass123! (regular),")
print("            testadmin@example.com/TestPass123! (Admins group)")
