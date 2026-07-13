import { apiFetch } from './client';

export function clearAllData(): Promise<void> {
  return apiFetch('/api/data', { method: 'DELETE' });
}
