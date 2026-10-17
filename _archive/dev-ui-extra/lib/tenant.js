// Tenant-from-subdomain, same idea as slotta-fe/src/lib/tenant-from-host.ts:
// "acme.staging.example.com" -> "acme" when ".staging.example.com" is a
// configured suffix.
//
// The real file HARDCODES its suffixes (.dev.slotta.ai, .slotta.dev,
// .slotta.ai), which is why a new staging domain needs a code change there.
// Here they come from NEXT_PUBLIC_TENANT_HOST_SUFFIXES (comma-separated,
// inlined at build time), e.g. ".staging.example.com,.example.com".
// Longer suffixes are tried first so "a.staging.x.com" isn't read as "a.staging".

const RESERVED_SUBDOMAINS = new Set(["www", "api", "admin", "dev", "staging"]);
const SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i;

const SUFFIXES = (process.env.NEXT_PUBLIC_TENANT_HOST_SUFFIXES || "")
  .split(",")
  .map((s) => s.trim().toLowerCase())
  .filter(Boolean)
  .map((s) => (s.startsWith(".") ? s : `.${s}`))
  .sort((a, b) => b.length - a.length);

export function normalizeHostname(hostHeader) {
  return (hostHeader || "").split(",")[0].split(":")[0].trim().toLowerCase();
}

// Behind Amplify's CDN the original host arrives in x-forwarded-host.
export function getRequestHost(headers) {
  return normalizeHostname(headers.get("x-forwarded-host") || headers.get("host") || "");
}

export function tenantFromHost(hostHeader) {
  const host = normalizeHostname(hostHeader);
  for (const suffix of SUFFIXES) {
    if (host.endsWith(suffix) && host.length > suffix.length) {
      const label = host.slice(0, -suffix.length);
      if (!label.includes(".") && SLUG_PATTERN.test(label) && !RESERVED_SUBDOMAINS.has(label)) {
        return label;
      }
    }
  }
  return null;
}
