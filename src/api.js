/**
 * Client for the Annapurna AI API.
 *
 * The backend is the single source of agronomic advice. This module never
 * computes a recommendation; when the API is unreachable it replays the last
 * response the API actually returned, clearly marked as cached.
 */

export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const TOKEN_KEY = 'annapurna-token';
const USER_KEY = 'annapurna-user';
const ANALYSIS_KEY = 'annapurna-last-analysis';

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }

  get isOffline() {
    return this.status === 0;
  }

  get isAuthError() {
    return this.status === 401;
  }
}

/** localStorage throws in private-mode Safari and when storage is full. */
function safeStorage(action, fallback = null) {
  try {
    return action();
  } catch {
    return fallback;
  }
}

export function getToken() {
  return safeStorage(() => localStorage.getItem(TOKEN_KEY));
}

export function getStoredUser() {
  const raw = safeStorage(() => localStorage.getItem(USER_KEY));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    safeStorage(() => localStorage.removeItem(USER_KEY));
    return null;
  }
}

export function storeSession(user, token) {
  safeStorage(() => {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    localStorage.setItem(TOKEN_KEY, token);
  });
}

export function clearSession() {
  safeStorage(() => {
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(TOKEN_KEY);
  });
}

let onAuthFailure = () => {};

/** Register a callback invoked whenever the server rejects our session. */
export function setAuthFailureHandler(handler) {
  onAuthFailure = handler;
}

async function request(path, { method = 'GET', body, auth = false, formData } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  if (auth) {
    const token = getToken();
    if (!token) {
      onAuthFailure();
      throw new ApiError('Sign in to continue', 401);
    }
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined)
    });
  } catch (cause) {
    throw new ApiError('Cannot reach the Annapurna API', 0, cause?.message);
  }

  if (response.status === 401) {
    clearSession();
    onAuthFailure();
    throw new ApiError('Session expired. Sign in again.', 401);
  }

  if (response.status === 204) return null;

  let payload = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    payload = await response.json().catch(() => null);
  } else {
    payload = await response.text().catch(() => null);
  }

  if (!response.ok) {
    const detail =
      (payload && typeof payload === 'object' && payload.detail) ||
      (typeof payload === 'string' ? payload : null);
    throw new ApiError(describeError(response.status, detail), response.status, detail);
  }

  return payload;
}

function describeError(status, detail) {
  if (typeof detail === 'string' && detail) return detail;
  if (status === 409) return 'That phone number is already registered';
  if (status === 422) return 'Some farm inputs are missing or out of range';
  if (status === 429) return 'Too many attempts. Please wait a few minutes.';
  if (status >= 500) return 'The Annapurna API had a problem. Try again shortly.';
  return `Request failed (HTTP ${status})`;
}

/** Convert the camelCase UI model into the snake_case API contract. */
export function toApiFarm(farm) {
  return {
    farmer_name: farm.farmerName || null,
    phone: /^\d{10}$/.test(farm.phone || '') ? farm.phone : null,
    location: farm.location,
    language: farm.language,
    season: farm.season,
    previous_crop: farm.previousCrop,
    soil_type: farm.soilType,
    market_priority: farm.marketPriority,
    land_size: Number(farm.landSize),
    ph: Number(farm.ph),
    nitrogen: Number(farm.nitrogen),
    phosphorus: Number(farm.phosphorus),
    potassium: Number(farm.potassium),
    temperature: Number(farm.temperature),
    humidity: Number(farm.humidity),
    rainfall: Number(farm.rainfall),
    budget: Number(farm.budget)
  };
}

export const api = {
  health: () => request('/health'),
  crops: () => request('/crops'),
  integrationStatus: () => request('/integrations/status'),

  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
  logout: () => request('/auth/logout', { method: 'POST', auth: true }),

  analysis: (farm) => request('/analysis', { method: 'POST', body: toApiFarm(farm) }),
  chat: (question, crop, farm) =>
    request('/chat', { method: 'POST', body: { question, crop, farm: toApiFarm(farm) } }),

  disease: (file, crop) => {
    const formData = new FormData();
    formData.append('file', file);
    if (crop) formData.append('crop', crop);
    return request('/disease', { method: 'POST', formData });
  },

  listHistory: () => request('/history', { auth: true }),
  saveHistory: (record) => request('/history', { method: 'POST', body: record, auth: true }),

  report: async (farm) => {
    const response = await fetch(`${API_BASE}/reports/recommendation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toApiFarm(farm))
    }).catch((cause) => {
      throw new ApiError('Cannot reach the Annapurna API', 0, cause?.message);
    });
    if (!response.ok) throw new ApiError(describeError(response.status), response.status);
    return response.text();
  }
};

/**
 * Cache of the last analysis the server produced, so an offline client can show
 * real previous advice instead of inventing new advice locally.
 */
export const analysisCache = {
  save(data, farm) {
    safeStorage(() =>
      localStorage.setItem(
        ANALYSIS_KEY,
        JSON.stringify({ data, farm, cachedAt: new Date().toISOString() })
      )
    );
  },

  load() {
    const raw = safeStorage(() => localStorage.getItem(ANALYSIS_KEY));
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (!parsed?.data?.recommendations?.length) return null;
      return parsed;
    } catch {
      safeStorage(() => localStorage.removeItem(ANALYSIS_KEY));
      return null;
    }
  },

  clear() {
    safeStorage(() => localStorage.removeItem(ANALYSIS_KEY));
  }
};

/** `crypto.randomUUID` needs a secure context; LAN testing over http does not have one. */
export function makeId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
