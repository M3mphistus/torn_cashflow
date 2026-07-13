import { apiFetch } from './client';
import type { WarModeDTO } from '../types/api';

export function getWarMode(): Promise<WarModeDTO> {
  return apiFetch('/api/settings/war-mode');
}

export function setWarMode(active: boolean): Promise<WarModeDTO> {
  return apiFetch('/api/settings/war-mode', { method: 'PUT', body: JSON.stringify({ active }) });
}
