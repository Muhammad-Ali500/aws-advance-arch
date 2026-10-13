export const COGNITO_CONFIG = {
  UserPoolId: import.meta.env.VITE_USER_POOL_ID,
  ClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID,
  ...(import.meta.env.VITE_COGNITO_ENDPOINT
    ? { endpoint: import.meta.env.VITE_COGNITO_ENDPOINT }
    : {}),
};

export const API_BASE_URL =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://localhost:8080/api"
    : "/api";
