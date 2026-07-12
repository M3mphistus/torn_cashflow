import type { SnapshotDTO } from '../types/api';

export function snapshotsToCsv(snapshots: SnapshotDTO[]): string {
  if (snapshots.length === 0) return '';

  const headers = Object.keys(snapshots[0]) as (keyof SnapshotDTO)[];
  const lines = [headers.join(',')];
  for (const snapshot of snapshots) {
    lines.push(headers.map((h) => csvCell(snapshot[h])).join(','));
  }
  return lines.join('\n');
}

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
