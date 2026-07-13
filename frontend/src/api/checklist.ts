import { apiFetch } from './client';
import type { ChecklistTaskDTO, RepeatType } from '../types/api';

export interface ChecklistTaskInput {
  title: string;
  description: string;
  repeatType: RepeatType;
  repeatIntervalDays: number | null;
}

export function getChecklist(): Promise<{ tasks: ChecklistTaskDTO[] }> {
  return apiFetch('/api/checklist');
}

export function createTask(input: ChecklistTaskInput): Promise<{ task: ChecklistTaskDTO }> {
  return apiFetch('/api/checklist', { method: 'POST', body: JSON.stringify(input) });
}

export function updateTask(id: number, input: ChecklistTaskInput): Promise<{ task: ChecklistTaskDTO }> {
  return apiFetch(`/api/checklist/${id}`, { method: 'PATCH', body: JSON.stringify(input) });
}

export function deleteTask(id: number): Promise<void> {
  return apiFetch(`/api/checklist/${id}`, { method: 'DELETE' });
}

export function setTaskDone(id: number, done: boolean): Promise<{ task: ChecklistTaskDTO }> {
  return apiFetch(`/api/checklist/${id}/done`, { method: 'POST', body: JSON.stringify({ done }) });
}
