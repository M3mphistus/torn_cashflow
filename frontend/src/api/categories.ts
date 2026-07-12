import { apiFetch } from './client';
import type { CategoryDTO, TitleSummaryRow } from '../types/api';

export function getCategories(): Promise<{ categories: CategoryDTO[] }> {
  return apiFetch('/api/categories');
}

export function createCategory(name: string): Promise<{ name: string }> {
  return apiFetch('/api/categories', { method: 'POST', body: JSON.stringify({ name }) });
}

export function deleteCategory(name: string): Promise<void> {
  return apiFetch(`/api/categories/${encodeURIComponent(name)}`, { method: 'DELETE' });
}

export function getTitleSummary(filterCategory?: string): Promise<{ rows: TitleSummaryRow[] }> {
  const qs = filterCategory ? `?filterCategory=${encodeURIComponent(filterCategory)}` : '';
  return apiFetch(`/api/categories/title-summary${qs}`);
}

export function reassignCategory(title: string, fromCategory: string, toCategory: string): Promise<{ updatedCount: number }> {
  return apiFetch('/api/categories/reassign', {
    method: 'POST',
    body: JSON.stringify({ title, fromCategory, toCategory }),
  });
}
