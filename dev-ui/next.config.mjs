// API_PROXY_TARGET (optional, read at build time): when the ALB has no HTTPS
// domain yet, set it to http://<alb-dns-name> and the Next.js server proxies
// /api/* and /auth/* to it server-side (no browser mixed-content block).
// When NEXT_PUBLIC_API_BASE_URL is set instead, this isn't needed.
const apiProxy = (process.env.API_PROXY_TARGET || "").replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    if (!apiProxy) return [];
    return [
      { source: "/api/:path*", destination: `${apiProxy}/api/:path*` },
      { source: "/auth/:path*", destination: `${apiProxy}/auth/:path*` },
    ];
  },
};

export default nextConfig;
