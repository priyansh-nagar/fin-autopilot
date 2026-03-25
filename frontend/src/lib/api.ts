const ENV_BASE = import.meta.env.VITE_API_URL?.trim();

function getBaseUrl() {
  const normalized = ENV_BASE?.replace(/\/$/, '');
  if (normalized) {
    return normalized.endsWith('/api') ? normalized : `${normalized}/api`;
  }
  if (import.meta.env.DEV) return 'http://localhost:8000/api';
  // Production fallback: use same-domain Vercel Python function at /api
  return '/api';
}

function apiUrl(path: string) {
  return `${getBaseUrl()}${path}`;
}

async function fetchJson(url: string, options: RequestInit) {
  const timeoutMs = (options as any).timeoutMs ?? 45000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    if (!res.ok) {
      const text = (await res.text()).trim();
      const detail = text || `${res.status} ${res.statusText}`.trim();
      throw new Error(`API ${res.status}: ${detail}`);
    }
    return res.json();
  } catch (error: any) {
    if (error?.name === 'AbortError') {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s for ${url}.`);
    }
    if (error instanceof TypeError) {
      throw new Error(
        `Network error while reaching ${url}. Verify backend is deployed and CORS allows your frontend domain.`
      );
    }
    if (!error?.message) {
      throw new Error(`Unknown upload error while calling ${url}. Check backend logs and CORS settings.`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export async function uploadAndParse(file: File) {
  const form = new FormData();
  form.append('file', file);
  return fetchJson(apiUrl('/parse'), { method: 'POST', body: form, timeoutMs: 90000 } as RequestInit);
}

export async function runDetection(data: object) {
  return fetchJson(apiUrl('/detect'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function askFinBot(messages: object[], context: object) {
  return fetchJson(apiUrl('/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, context }),
  });
}
