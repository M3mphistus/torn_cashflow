import { apiFetch } from './client';
import type { SessionDTO } from '../types/api';

export function login(apiKey: string): Promise<SessionDTO> {
  return apiFetch<SessionDTO>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ apiKey }),
  });
}

export function logout(): Promise<void> {
  return apiFetch<void>('/api/auth/logout', { method: 'POST' });
}

export function getMe(): Promise<SessionDTO> {
  return apiFetch<SessionDTO>('/api/auth/me');
}
