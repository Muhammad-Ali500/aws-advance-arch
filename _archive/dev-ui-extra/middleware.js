import { NextResponse } from "next/server";

import { getRequestHost, tenantFromHost } from "./lib/tenant";

// Runs on every page request (like slotta-fe/middleware.ts). Middleware only
// works when Amplify deploys the app as SSR ("WEB_COMPUTE"); on a static
// deployment it silently never runs - the page would then show
// tenantSource "none", which is the quickest way to spot that mistake.
export function middleware(request) {
  const host = getRequestHost(request.headers);
  const fromHost = tenantFromHost(host);
  const fromQuery = request.nextUrl.searchParams.get("tenant");
  const fallback = process.env.NEXT_PUBLIC_DEFAULT_BUSINESS_CODE || "";

  const tenant = fromHost || fromQuery || fallback;
  const source = fromHost ? "subdomain" : fromQuery ? "query" : fallback ? "default" : "none";

  const headers = new Headers(request.headers);
  headers.set("x-tenant", tenant);
  headers.set("x-tenant-source", source);
  headers.set("x-request-host", host);
  return NextResponse.next({ request: { headers } });
}

export const config = {
  matcher: ["/((?!_next/|api/|auth/|favicon.ico).*)"],
};
