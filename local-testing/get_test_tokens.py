"""
Gets real access tokens for the two seeded test users, by performing the
actual Cognito USER_PASSWORD_AUTH flow against cognito-local - the same
flow the frontend's amazon-cognito-identity-js library performs, just
driven here via boto3 so we can test the backend with curl.
"""
import sys

import boto3

ENDPOINT = "http://localhost:9229"

client = boto3.client(
    "cognito-idp",
    endpoint_url=ENDPOINT,
    region_name="local",
    aws_access_key_id="local",
    aws_secret_access_key="local",
)


def get_token(client_id, username, password):
    resp = client.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    return resp["AuthenticationResult"]["AccessToken"]


if __name__ == "__main__":
    ui_client_id = sys.argv[1]
    admin_client_id = sys.argv[2]

    user_token = get_token(ui_client_id, "testuser@example.com", "TestPass123!")
    admin_token = get_token(admin_client_id, "testadmin@example.com", "TestPass123!")

    print("USER_TOKEN=" + user_token)
    print("ADMIN_TOKEN=" + admin_token)
