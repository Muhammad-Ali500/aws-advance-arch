"use client";

import { useState } from "react";

// NEXT_PUBLIC_API_BASE_URL set -> call the API domain directly (real-project mode).
// Unset -> same-origin /api and /auth, proxied by next.config.mjs (API_PROXY_TARGET).
function apiBase() {
  const fromEnv = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  return ["localhost", "127.0.0.1"].includes(window.location.hostname) ? "http://localhost:3000" : "";
}

export default function ClientPanel() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(null);
  const [result, setResult] = useState("");

  async function call(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    const resp = await fetch(`${apiBase()}${path}`, { method, headers, body: body && JSON.stringify(body) });
    return { status: resp.status, data: await resp.json().catch(() => ({})) };
  }

  const show = (v) => setResult(JSON.stringify(v, null, 2));

  async function login() {
    const res = await call("POST", "/auth/login", { email, password });
    setToken(res.data.access_token || null);
    show(res.data.access_token ? { signedIn: true } : res);
  }

  return (
    <div className="card">
      <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" placeholder="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button onClick={login}>Sign in</button>
      <button onClick={async () => show(await call("GET", "/api/me"))}>/api/me</button>
      <button onClick={async () => show(await call("POST", "/api/items", { text: "hello" }))}>Add item</button>
      <button onClick={async () => show(await call("GET", "/api/items"))}>List items</button>
      <pre>{result}</pre>
    </div>
  );
}
