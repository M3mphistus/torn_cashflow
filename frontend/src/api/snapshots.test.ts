import { describe, expect, it, vi } from 'vitest';
import * as client from './client';
import { getSnapshots, getLatestSnapshot, updateSnapshotNote } from './snapshots';

describe('getSnapshots', () => {
  it('omits the querystring entirely when no params are given', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshots: [] });
    await getSnapshots();
    expect(spy).toHaveBeenCalledWith('/api/snapshots');
  });

  it('includes only the params that were given', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshots: [] });
    await getSnapshots(1700000000);
    expect(spy).toHaveBeenCalledWith('/api/snapshots?startTs=1700000000');
  });

  it('includes both params when both are given', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshots: [] });
    await getSnapshots(1700000000, 1700600000);
    expect(spy).toHaveBeenCalledWith('/api/snapshots?startTs=1700000000&endTs=1700600000');
  });
});

describe('getLatestSnapshot', () => {
  it('calls the latest endpoint', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshot: null });
    await getLatestSnapshot();
    expect(spy).toHaveBeenCalledWith('/api/snapshots/latest');
  });
});

describe('updateSnapshotNote', () => {
  it('PATCHes the note as JSON', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshot: {} as never });
    await updateSnapshotNote(501, 'War week 1');
    expect(spy).toHaveBeenCalledWith('/api/snapshots/501/note', {
      method: 'PATCH',
      body: JSON.stringify({ note: 'War week 1' }),
    });
  });
});
