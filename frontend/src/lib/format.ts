export function formatCurrency(amount: number | null): string {
  if (amount === null) return 'n/a';
  const rounded = Math.round(amount);
  const sign = rounded < 0 ? '-' : '';
  return `${sign}$${Math.abs(rounded).toLocaleString('en-US')}`;
}

export function formatTimestamp(ts: number): string {
  const iso = new Date(ts * 1000).toISOString();
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
}

export function formatDays(days: number): string {
  return days.toFixed(1);
}
