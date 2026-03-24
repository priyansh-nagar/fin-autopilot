const ENV_BASE = import.meta.env.VITE_API_URL?.trim();
const BASE = ENV_BASE || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin);

function apiUrl(path: string) {
  return `${BASE}${path}`;
}

async function fetchJson(url: string, options: RequestInit) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } catch (error: any) {
    if (error instanceof TypeError) {
      throw new Error(
        `Network error while reaching ${url}. Verify VITE_API_URL points to a live HTTPS backend and CORS allows your frontend domain.`
      );
    }
    throw error;
  }
}

export async function uploadAndParse(file: File) {
  const form = new FormData();
  form.append('file', file);
  return fetchJson(apiUrl('/api/parse'), { method: 'POST', body: form });
}

export async function runDetection(data: object) {
  return fetchJson(apiUrl('/api/detect'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function askFinBot(messages: object[], context: object) {
  return fetchJson(apiUrl('/api/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, context }),
  });
}
