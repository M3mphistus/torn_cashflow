import { describe, expect, it, vi } from 'vitest';
import * as client from './client';
import { getDashboard } from './dashboard';

describe('getDashboard', () => {
  it('calls /api/dashboard with startTs and endTs in the querystring', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({} as never);

    await getDashboard(1700000000, 1700600000);

    expect(spy).toHaveBeenCalledWith('/api/dashboard?startTs=1700000000&endTs=1700600000');
  });
});
