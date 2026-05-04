// In dev the Vite proxy forwards /user, /jobs, /sessions to the API — no BASE_URL needed.
// In production set VITE_API_URL to the API Gateway URL.
const BASE_URL = import.meta.env.PROD ? (import.meta.env.VITE_API_URL ?? '') : '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export default request;
