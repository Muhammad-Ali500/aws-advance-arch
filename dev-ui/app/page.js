import { headers } from "next/headers";

import ClientPanel from "./ClientPanel";

// Rendered on the server per request. If "renderedAt" never changes on reload,
// Amplify deployed the app as static instead of SSR (WEB_COMPUTE).
// "host" shows which (sub)domain served the page - use it to check the
// wildcard *.domain mapping, like Slotta's tenant subdomains.
export const dynamic = "force-dynamic";

export default async function Page() {
  const h = await headers();
  const host = h.get("x-forwarded-host") || h.get("host");

  return (
    <main>
      <h1>dev-ui (Next.js SSR on Amplify)</h1>
      <div className="card">
        <pre>{JSON.stringify({ host, renderedAt: new Date().toISOString() }, null, 2)}</pre>
      </div>
      <ClientPanel />
    </main>
  );
}
