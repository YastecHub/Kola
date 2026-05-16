const DEFAULT_BACKEND_URL = "https://kola-wib6.onrender.com";

export function getKolaBackendConfig() {
  const baseUrl =
    process.env.KOLA_API_URL ??
    process.env.NEXT_PUBLIC_KOLA_API_URL ??
    DEFAULT_BACKEND_URL;
  const apiKey = process.env.KOLA_API_KEY ?? null;

  return {
    baseUrl: baseUrl.replace(/\/$/, ""),
    apiKey,
  };
}

export async function fetchKolaBackend(path: string, init: RequestInit = {}) {
  const { baseUrl, apiKey } = getKolaBackendConfig();
  const headers = new Headers(init.headers);

  if (apiKey) {
    headers.set("X-API-Key", apiKey);
  }

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
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : "KOLA backend request failed.";
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