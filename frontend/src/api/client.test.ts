import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, ApiError } from './client';

describe('apiFetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('always sends credentials: include', async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('/api/whatever');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = (fetchMock.mock.calls[0] as unknown) as [unknown, RequestInit];
    expect(options.credentials).toBe('include');
  });

  it('returns parsed JSON on a 2xx response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ hello: 'world' }), { status: 200 })),
    );

    const result = await apiFetch<{ hello: string }>('/api/whatever');
    expect(result).toEqual({ hello: 'world' });
  });

  it('returns undefined on a 204 response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })));

    const result = await apiFetch('/api/whatever');
    expect(result).toBeUndefined();
  });

  it('throws a typed ApiError parsed from the error envelope on non-2xx', async () => {
    const body = { error: { message: 'Incorrect API key.', code: 'invalid_key', tornErrorCode: 2 } };
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status: 401 })));

    await expect(apiFetch('/api/auth/me')).rejects.toMatchObject({
      message: 'Incorrect API key.',
      code: 'invalid_key',
      tornErrorCode: 2,
      status: 401,
    });
    await expect(apiFetch('/api/auth/me')).rejects.toBeInstanceOf(ApiError);
  });

  it('defaults tornErrorCode to null when absent from the error envelope', async () => {
    const body = { error: { message: 'Category still in use.', code: 'category_in_use' } };
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status: 409 })));

    await expect(apiFetch('/api/categories/Job')).rejects.toMatchObject({ tornErrorCode: null });
  });
});
