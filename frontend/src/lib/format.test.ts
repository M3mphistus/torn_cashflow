import { describe, expect, it } from 'vitest';
import { formatCurrency, formatTimestamp, formatDays } from './format';

describe('formatCurrency', () => {
  it('formats a positive amount with thousands separators and no decimals', () => {
    expect(formatCurrency(1234567)).toBe('$1,234,567');
  });
  it('formats a negative amount', () => {
    expect(formatCurrency(-500)).toBe('-$500');
  });
  it('returns n/a for null', () => {
    expect(formatCurrency(null)).toBe('n/a');
  });
  it('rounds fractional amounts', () => {
    expect(formatCurrency(178571.4)).toBe('$178,571');
  });
});

describe('formatTimestamp', () => {
  it('formats a unix timestamp as UTC date + time', () => {
    expect(formatTimestamp(1730000000)).toBe('2024-10-27 03:33 UTC');
  });
});

describe('formatDays', () => {
  it('formats to one decimal place', () => {
    expect(formatDays(12.44)).toBe('12.4');
  });
});
