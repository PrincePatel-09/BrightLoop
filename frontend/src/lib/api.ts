const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const ACCESS_KEY = "brightloop.access";
const REFRESH_KEY = "brightloop.refresh";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

type Options = RequestInit & { skipAuth?: boolean; retry?: boolean };

async function parseError(response: Response) {
  try {
    const body = await response.json();
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item: { msg?: string }) => item.msg).join(", ")
      : body.detail || "Request failed";
    throw new ApiError(detail, response.status, body.code);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(response.statusText || "Request failed", response.status);
  }
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const access = getAccessToken();
  if (access && !options.skipAuth) {
    headers.set("Authorization", `Bearer ${access}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401 && !options.skipAuth && options.retry !== false) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return api<T>(path, { ...options, retry: false });
    }
  }

  if (!response.ok) {
    await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function downloadFile(path: string) {
  const request = () => fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${getAccessToken() || ""}` } });
  let response = await request();
  if (response.status === 401 && await tryRefresh()) response = await request();
  if (!response.ok) await parseError(response);
  const blob = await response.blob();
  const filename = response.headers.get("Content-Disposition")?.match(/filename="?([^";]+)"?/i)?.[1] || "invoice.pdf";
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function printFile(path: string) {
  const printWindow = window.open("about:blank", "_blank");
  if (!printWindow) throw new ApiError("Allow pop-ups to print this document", 400, "popup_blocked");
  try {
    const request = () => fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${getAccessToken() || ""}` } });
    let response = await request();
    if (response.status === 401 && await tryRefresh()) response = await request();
    if (!response.ok) await parseError(response);
    const url = URL.createObjectURL(await response.blob());
    printWindow.location.replace(url);
    printWindow.addEventListener("load", () => printWindow.print(), { once: true });
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (error) {
    printWindow.close();
    throw error;
  }
}

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) {
    clearTokens();
    return false;
  }
  try {
    const data = await api<{ access_token: string; refresh_token: string }>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refresh }),
      skipAuth: true,
    });
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}
