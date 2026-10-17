import { API_BASE_URL } from "./config.js";

const $ = (id) => document.getElementById(id);
const show = (data) => ($("result").textContent = JSON.stringify(data, null, 2));
let token = null;

async function call(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE_URL}${path}`, { method, headers, body: body && JSON.stringify(body) });
  const data = await resp.json().catch(() => ({}));
  return { status: resp.status, data };
}

$("login-btn").onclick = async () => {
  const res = await call("POST", "/auth/login", { email: $("email").value, password: $("password").value });
  token = res.data.access_token || null;
  show(token ? { signedIn: true } : res);
};

document.querySelectorAll("[data-path]").forEach((btn) => {
  btn.onclick = async () => show(await call("GET", btn.dataset.path));
});
