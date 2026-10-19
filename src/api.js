// One HTTP layer for the whole app.
//
// The previous code did `catch { setApiStatus('Backend offline: run FastAPI on port 8000') }`
// around every call, so a 422 validation error, a 429 rate limit, a 503 missing-API-key and an
// actual network failure all told the farmer the same wrong thing. `ApiError` carries the status
// and the server's own message so each screen can say what really happened.

export const API_BASE = import.meta.env.VITE_API_URL || '/api';

const ACCESS_TOKEN_KEY = 'annapurna-access-token';
const REFRESH_TOKEN_KEY = 'annapurna-refresh-token';

export class ApiError extends Error {
  constructor(status, message, { requestId, retryAfter, fields } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.requestId = requestId;
    this.retryAfter = retryAfter;
    this.fields = fields;
  }

  get isOffline() {
    return this.status === 0;
  }

  get isAuth() {
    return this.status === 401;
  }

  get needsConfiguration() {
    return this.status === 503;
  }
}

// localStorage throws in private mode and in some embedded webviews. Every access is guarded so a
// blocked store degrades to "signed out" instead of a blank page.
export const storage = {
  get(key) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      window.localStorage.setItem(key, value);
      return true;
    } catch {
      return false;
    }
  },
  remove(key) {
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* nothing to do: the store is unavailable */
    }
  },
  json(key, fallback) {
    const raw = storage.get(key);
    if (!raw) return fallback;
    try {
      return JSON.parse(raw);
    } catch {
      storage.remove(key);
      return fallback;
    }
  },
};

export const tokens = {
  access: () => storage.get(ACCESS_TOKEN_KEY),
  refresh: () => storage.get(REFRESH_TOKEN_KEY),
  save(pair) {
    storage.set(ACCESS_TOKEN_KEY, pair.access_token);
    storage.set(REFRESH_TOKEN_KEY, pair.refresh_token);
  },
  clear() {
    storage.remove(ACCESS_TOKEN_KEY);
    storage.remove(REFRESH_TOKEN_KEY);
  },
};

function describe(status, payload) {
  if (payload && typeof payload.detail === 'string') return payload.detail;
  if (Array.isArray(payload?.detail)) {
    // FastAPI validation errors: name the field rather than dumping the raw array.
    return payload.detail
      .map((item) => {
        const field = (item.loc || []).filter((part) => part !== 'body').join(' → ');
        return field ? `${field}: ${item.msg}` : item.msg;
      })
      .join('; ');
  }
  const byStatus = {
    400: 'That request could not be processed.',
    401: 'Please sign in again.',
    403: 'You do not have access to that.',
    404: 'That record no longer exists.',
    409: 'That conflicts with something already saved.',
    413: 'That file is too large.',
    415: 'That file type is not supported.',
    422: 'Some of the values entered are not valid.',
    429: 'Too many requests. Please wait a moment.',
    500: 'Something went wrong on the server.',
    503: 'That feature is not configured on the server yet.',
  };
  return byStatus[status] || `Request failed (${status}).`;
}

function fieldErrors(payload) {
  if (!Array.isArray(payload?.detail)) return undefined;
  const fields = {};
  for (const item of payload.detail) {
    const name = (item.loc || []).filter((part) => part !== 'body').pop();
    if (name) fields[name] = item.msg;
  }
  return Object.keys(fields).length ? fields : undefined;
}

let refreshInFlight = null;

async function refreshAccessToken() {
  const refreshToken = tokens.refresh();
  if (!refreshToken) return false;
  // Several requests can 401 at once; they must share one refresh, not race it.
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) {
          tokens.clear();
          return false;
        }
        tokens.save(await response.json());
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

export async function request(path, { method = 'GET', body, signal, auth = false, raw = false, retry = true } = {}) {
  const headers = {};
  let payload = body;
  if (body !== undefined && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  const accessToken = tokens.access();
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { method, headers, body: payload, signal });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new ApiError(0, 'Cannot reach the Annapurna server. Check your connection and that the backend is running.');
  }

  if (response.status === 401 && retry && tokens.refresh()) {
    if (await refreshAccessToken()) {
      return request(path, { method, body, signal, auth, raw, retry: false });
    }
  }

  if (response.status === 204) return null;

  if (raw && response.ok) return response.blob();

  let data = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else if (response.ok) {
    return response.text();
  }

  if (!response.ok) {
    throw new ApiError(response.status, describe(response.status, data), {
      requestId: response.headers.get('x-request-id'),
      retryAfter: Number(response.headers.get('retry-after')) || undefined,
      fields: fieldErrors(data),
    });
  }
  return data;
}

export const api = {
  health: () => request('/health'),
  crops: () => request('/crops'),
  integrations: () => request('/integrations/status'),
  analysis: (farm, signal) => request('/analysis', { method: 'POST', body: farm, signal }),
  recommendations: (farm, signal) => request('/recommendations', { method: 'POST', body: farm, signal }),
  seasonPlan: (payload, signal) => request('/finance/season-plan', { method: 'POST', body: payload, signal }),
  chat: (payload, signal) => request('/chat', { method: 'POST', body: payload, signal }),
  disease: (formData, signal) => request('/disease', { method: 'POST', body: formData, signal }),
  pdfReport: (payload) => request('/reports/pdf', { method: 'POST', body: payload, raw: true }),
  textReport: (farm) => request('/reports/recommendation', { method: 'POST', body: farm }),

  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
  logout: (refreshToken) => request('/auth/logout', { method: 'POST', body: { refresh_token: refreshToken } }),
  me: () => request('/auth/me'),
  updateMe: (payload) => request('/auth/me', { method: 'PATCH', body: payload }),
  deleteAccount: () => request('/auth/me', { method: 'DELETE' }),

  listPlans: (limit = 20, offset = 0) => request(`/plans?limit=${limit}&offset=${offset}`),
  getPlan: (id) => request(`/plans/${id}`),
  savePlan: (payload) => request('/plans', { method: 'POST', body: payload }),
  deletePlan: (id) => request(`/plans/${id}`, { method: 'DELETE' }),

  listFinancePlans: () => request('/finance/plans'),
  saveFinancePlan: (payload) => request('/finance/plans', { method: 'POST', body: payload }),

  listProfiles: () => request('/profiles'),
  saveProfile: (payload) => request('/profiles', { method: 'PUT', body: payload }),
  deleteProfile: (id) => request(`/profiles/${id}`, { method: 'DELETE' }),
};

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoking synchronously can cancel the download in Safari; give the browser a tick.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
