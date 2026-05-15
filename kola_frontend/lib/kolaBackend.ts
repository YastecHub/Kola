const DEFAULT_BACKEND_URL = "http://127.0.0.1:8001";

export function getKolaBackendConfig() {
  const baseUrl = process.env.KOLA_API_URL ?? process.env.NEXT_PUBLIC_KOLA_API_URL ?? DEFAULT_BACKEND_URL;
  const apiKey = process.env.KOLA_API_KEY;

  return {
    baseUrl: baseUrl.replace(/\/$/, ""),
    apiKey,
  };
}

export function requireKolaApiKey() {
  const { apiKey } = getKolaBackendConfig();

  if (!apiKey) {
    throw new Error("Missing KOLA_API_KEY in kola_frontend environment.");
  }

  return apiKey;
}

export async function fetchKolaBackend(path: string, init: RequestInit = {}) {
  const { baseUrl } = getKolaBackendConfig();
  const apiKey = requireKolaApiKey();
  const headers = new Headers(init.headers);

  headers.set("X-API-Key", apiKey);

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
}

export async function proxyKolaJson(path: string, init: RequestInit = {}) {
  const response = await fetchKolaBackend(path, init);
  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "KOLA backend request failed.";
    return {
      ok: false,
      status: response.status,
      body: { error: detail },
    };
  }

  return {
    ok: true,
    status: response.status,
    body,
  };
}
