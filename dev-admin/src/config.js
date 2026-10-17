// VITE_API_BASE_URL set (e.g. https://api.your-domain.com) -> browser calls the
// API domain directly, like the real admin UI (needs HTTPS on the ALB).
// Unset -> same-origin "/api" and "/auth", proxied to the ALB by an Amplify
// rewrite rule (practice mode without a domain).
const isLocal = ["localhost", "127.0.0.1"].includes(location.hostname);

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || (isLocal ? "http://localhost:3000" : "")).replace(/\/$/, "");
