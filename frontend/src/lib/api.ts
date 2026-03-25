const ENV_BASE = import.meta.env.VITE_API_URL?.trim();

function getBaseUrl() {
  if (ENV_BASE) return ENV_BASE.replace(/\/$/, '');
  if (import.meta.env.DEV) return 'http://localhost:8000';
  throw new Error(
    'VITE_API_URL is not configured for production. Set it to your backend URL (e.g. https://your-backend-domain).'
  );
}

function apiUrl(path: string) {
  return `${getBaseUrl()}${path}`;
}

async function fetchJson(url: string, options: RequestInit) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      const text = (await res.text()).trim();
      const detail = text || `${res.status} ${res.statusText}`.trim();
      throw new Error(`API ${res.status}: ${detail}`);
    }
    return res.json();
  } catch (error: any) {
    if (error instanceof TypeError) {
      throw new Error(
        `Network error while reaching ${url}. Verify VITE_API_URL points to a live HTTPS backend and CORS allows your frontend domain.`
      );
    }
    if (!error?.message) {
      throw new Error(`Unknown upload error while calling ${url}. Check backend logs and CORS settings.`);
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
