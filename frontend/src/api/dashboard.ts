import { apiFetch } from './client';
import type { DashboardDTO } from '../types/api';

export function getDashboard(startTs: number, endTs: number): Promise<DashboardDTO> {
  const params = new URLSearchParams({ startTs: String(startTs), endTs: String(endTs) });
  return apiFetch<DashboardDTO>(`/api/dashboard?${params.toString()}`);
}
