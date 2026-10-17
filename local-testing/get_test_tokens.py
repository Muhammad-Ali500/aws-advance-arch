"""
Gets access tokens for the seeded test users the same way the frontends do:
by calling the BACKEND's POST /auth/login (which runs AdminInitiateAuth with
ADMIN_USER_PASSWORD_AUTH). Use the tokens for curl tests.

Usage: python local-testing/get_test_tokens.py [backend_url]
       (default backend_url http://localhost:3000)
"""
import sys

import requests

BACKEND = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"

for label, email in (("USER", "testuser@example.com"), ("ADMIN", "testadmin@example.com"), ("SUPER", "testsuper@example.com")):
    resp = requests.post(f"{BACKEND}/auth/login", json={"email": email, "password": "TestPass123!"}, timeout=10)
    resp.raise_for_status()
    print(f"{label}_TOKEN={resp.json()['access_token']}")
