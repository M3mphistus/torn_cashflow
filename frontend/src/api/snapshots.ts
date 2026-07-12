import { apiFetch } from './client';
import type { SnapshotDTO } from '../types/api';

export function getSnapshots(startTs?: number, endTs?: number): Promise<{ snapshots: SnapshotDTO[] }> {
  const params = new URLSearchParams();
  if (startTs !== undefined) params.set('startTs', String(startTs));
  if (endTs !== undefined) params.set('endTs', String(endTs));
  const qs = params.toString();
  return apiFetch<{ snapshots: SnapshotDTO[] }>(`/api/snapshots${qs ? `?${qs}` : ''}`);
}

export function getLatestSnapshot(): Promise<{ snapshot: SnapshotDTO | null }> {
  return apiFetch<{ snapshot: SnapshotDTO | null }>('/api/snapshots/latest');
}

export function updateSnapshotNote(id: number, note: string): Promise<{ snapshot: SnapshotDTO }> {
  return apiFetch<{ snapshot: SnapshotDTO }>(`/api/snapshots/${id}/note`, {
    method: 'PATCH',
    body: JSON.stringify({ note }),
  });
}
