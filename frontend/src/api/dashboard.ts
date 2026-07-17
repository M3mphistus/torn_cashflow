import { apiFetch } from './client';
import type { DashboardBoundsDTO, DashboardDTO } from '../types/api';

export function getDashboard(startTs: number, endTs: number): Promise<DashboardDTO> {
  const params = new URLSearchParams({ startTs: String(startTs), endTs: String(endTs) });
  return apiFetch<DashboardDTO>(`/api/dashboard?${params.toString()}`);
}

export function getDashboardBounds(): Promise<DashboardBoundsDTO> {
  return apiFetch<DashboardBoundsDTO>('/api/dashboard/bounds');
}
