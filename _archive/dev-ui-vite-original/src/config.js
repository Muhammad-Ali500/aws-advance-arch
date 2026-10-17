// Cognito pool/client config comes from Vite env vars - set via Amplify
// Hosting's "Environment variables" in production, or a local .env file
// (gitignored) for local testing against cognito-local.
export const COGNITO_CONFIG = {
  UserPoolId: import.meta.env.VITE_USER_POOL_ID,
  ClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
  // Only set for local testing against cognito-local; leave unset in
  // production so the library uses the real regional AWS Cognito endpoint.
  ...(import.meta.env.VITE_COGNITO_ENDPOINT
    ? { endpoint: import.meta.env.VITE_COGNITO_ENDPOINT }
    : {}),
};

// In production (served from Amplify), /api/* is proxied server-side to the
// backend ALB via an Amplify rewrite rule - no mixed-content issue, since
// the browser only ever talks to the Amplify HTTPS domain. For local
// testing (no Amplify rewrite available), call the local backend directly.
export const API_BASE_URL =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://localhost:8080/api"
    : "/api";
