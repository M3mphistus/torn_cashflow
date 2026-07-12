import { apiFetch } from './client';
import type { GrantScope, LifetimeGrantDTO } from '../types/api';

export function getLifetimeGrants(): Promise<{ grants: LifetimeGrantDTO[] }> {
  return apiFetch('/api/admin/lifetime-grants');
}

export function createLifetimeGrant(scope: GrantScope, key: number): Promise<void> {
  return apiFetch('/api/admin/lifetime-grants', {
    method: 'POST',
    body: JSON.stringify({ scope, key }),
  });
}

export function deleteLifetimeGrant(scope: GrantScope, key: number): Promise<void> {
  return apiFetch('/api/admin/lifetime-grants', {
    method: 'DELETE',
    body: JSON.stringify({ scope, key }),
  });
}
