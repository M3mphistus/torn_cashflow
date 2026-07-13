import { apiFetch } from './client';
import type { FullHistoryJobDTO, FullHistoryJobStartDTO, SyncIncrementalResultDTO } from '../types/api';

export function syncIncremental(): Promise<SyncIncrementalResultDTO> {
  return apiFetch<SyncIncrementalResultDTO>('/api/sync/incremental', { method: 'POST' });
}

export function startFullHistorySync(): Promise<FullHistoryJobStartDTO> {
  return apiFetch<FullHistoryJobStartDTO>('/api/sync/full-history', { method: 'POST' });
}

export function getFullHistoryJob(jobId: number): Promise<FullHistoryJobDTO> {
  return apiFetch<FullHistoryJobDTO>(`/api/sync/full-history/${jobId}`);
}
