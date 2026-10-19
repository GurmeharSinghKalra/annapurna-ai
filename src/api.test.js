import { describe, expect, it, vi, beforeEach } from 'vitest';
import { ApiError, request, storage, tokens } from './api.js';

function respond({ status = 200, body = null, headers = {} } = {}) {
  return new Response(body === null ? null : JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...headers },
  });
}

beforeEach(() => {
  tokens.clear();
});

describe('error translation', () => {
  it('reports a network failure as offline, not as a server error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const error = await request('/health').catch((caught) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.isOffline).toBe(true);
    expect(error.status).toBe(0);
  });

  it("surfaces the server's own message instead of a generic one", async () => {
    // The old client turned every non-2xx into "Backend offline: run FastAPI on port 8000".
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      respond({ status: 503, body: { detail: 'Live mandi prices need AGMARKNET_API_KEY.' } })
    ));
    const error = await request('/market', { method: 'POST' }).catch((caught) => caught);
    expect(error.message).toContain('AGMARKNET_API_KEY');
    expect(error.needsConfiguration).toBe(true);
    expect(error.isOffline).toBe(false);
  });

  it('names the offending field for a validation error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond({
      status: 422,
      body: { detail: [{ loc: ['body', 'ph'], msg: 'Input should be less than or equal to 10' }] },
    })));
    const error = await request('/analysis', { method: 'POST' }).catch((caught) => caught);
    expect(error.message).toContain('ph');
    expect(error.fields.ph).toContain('less than or equal to 10');
  });

  it('carries the retry delay from a rate-limit response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      respond({ status: 429, body: { detail: 'Too many requests.' }, headers: { 'retry-after': '42' } })
    ));
    const error = await request('/chat', { method: 'POST' }).catch((caught) => caught);
    expect(error.retryAfter).toBe(42);
  });

  it('carries the request id so a report can reference it', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      respond({ status: 500, body: { detail: 'boom' }, headers: { 'x-request-id': 'abc123' } })
    ));
    const error = await request('/analysis', { method: 'POST' }).catch((caught) => caught);
    expect(error.requestId).toBe('abc123');
  });
});

describe('token handling', () => {
  it('refreshes once and retries the original request', async () => {
    tokens.save({ access_token: 'stale', refresh_token: 'refresh-1' });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(respond({ status: 401, body: { detail: 'expired' } }))
      .mockResolvedValueOnce(respond({ body: { access_token: 'fresh', refresh_token: 'refresh-2' } }))
      .mockResolvedValueOnce(respond({ body: { id: 'farmer-1' } }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await request('/auth/me');
    expect(result).toEqual({ id: 'farmer-1' });
    expect(tokens.access()).toBe('fresh');
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('gives up and clears tokens when the refresh itself fails', async () => {
    tokens.save({ access_token: 'stale', refresh_token: 'refresh-1' });
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(respond({ status: 401, body: { detail: 'expired' } }))
      .mockResolvedValueOnce(respond({ status: 401, body: { detail: 'bad refresh' } })));

    const error = await request('/auth/me').catch((caught) => caught);
    expect(error.isAuth).toBe(true);
    expect(tokens.access()).toBeNull();
  });

  it('does not attach an Authorization header when signed out', async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond({ body: {} }));
    vi.stubGlobal('fetch', fetchMock);
    await request('/health');
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });
});

describe('storage guard', () => {
  it('degrades instead of throwing when storage is blocked', () => {
    // Private mode and some embedded webviews throw on every access.
    const blocked = () => { throw new DOMException('denied'); };
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(blocked);
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(blocked);

    expect(() => storage.get('k')).not.toThrow();
    expect(storage.get('k')).toBeNull();
    expect(storage.set('k', 'v')).toBe(false);
    expect(storage.json('k', { fallback: true })).toEqual({ fallback: true });
  });

  it('discards corrupt stored JSON rather than crashing', () => {
    window.localStorage.setItem('broken', '{not json');
    expect(storage.json('broken', [])).toEqual([]);
    expect(window.localStorage.getItem('broken')).toBeNull();
  });
});
