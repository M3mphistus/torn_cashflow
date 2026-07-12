import { apiFetch } from './client';
import type { LogEntryDTO } from '../types/api';

export function getLogEntries(params: { startTs?: number; endTs?: number; category?: string } = {}): Promise<{ entries: LogEntryDTO[] }> {
  const qs = new URLSearchParams();
  if (params.startTs !== undefined) qs.set('startTs', String(params.startTs));
  if (params.endTs !== undefined) qs.set('endTs', String(params.endTs));
  if (params.category) qs.set('category', params.category);
  const s = qs.toString();
  return apiFetch<{ entries: LogEntryDTO[] }>(`/api/log-entries${s ? `?${s}` : ''}`);
}

export function getUncategorizedEntries(limit = 25): Promise<{ entries: LogEntryDTO[]; totalCount: number }> {
  return apiFetch(`/api/log-entries/uncategorized?limit=${limit}`);
}

export function getIgnoredEntries(limit = 25): Promise<{ entries: LogEntryDTO[]; totalCount: number }> {
  return apiFetch(`/api/log-entries/ignored?limit=${limit}`);
}

export function updateLogEntry(
  id: number,
  appCategory: string,
  userNote?: string,
): Promise<{ entry: LogEntryDTO; bulkUpdatedCount: number }> {
  return apiFetch(`/api/log-entries/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ appCategory, userNote: userNote ?? null }),
  });
}

export function ignoreLogEntry(id: number, userNote?: string): Promise<{ entry: LogEntryDTO; bulkUpdatedCount: number }> {
  return apiFetch(`/api/log-entries/${id}/ignore`, {
    method: 'POST',
    body: JSON.stringify({ userNote: userNote ?? null }),
  });
}

export function restoreLogEntry(id: number): Promise<{ entry: LogEntryDTO }> {
  return apiFetch(`/api/log-entries/${id}/restore`, { method: 'POST' });
}

export function recategorizePeriod(startTs: number, endTs: number, appCategory: string): Promise<{ updatedCount: number }> {
  return apiFetch('/api/log-entries/recategorize-period', {
    method: 'POST',
    body: JSON.stringify({ startTs, endTs, appCategory }),
  });
}
