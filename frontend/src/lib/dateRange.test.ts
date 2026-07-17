import { describe, expect, it } from 'vitest';
import { resolveTimeRange } from './dateRange';

const DAY = 86400;
const bounds = { minTs: 1_700_000_000, maxTs: 1_700_000_000 + 100 * DAY };

describe('resolveTimeRange', () => {
  it('today spans the calendar day (UTC) containing maxTs, clamped to bounds', () => {
    const dayStart = Math.floor(bounds.maxTs / DAY) * DAY;
    expect(resolveTimeRange('today', bounds)).toEqual({
      startTs: dayStart,
      endTs: Math.min(bounds.maxTs, dayStart + DAY - 1),
    });
  });

  it('yesterday spans the calendar day (UTC) before maxTs, clamped to bounds', () => {
    const dayStart = Math.floor(bounds.maxTs / DAY) * DAY;
    expect(resolveTimeRange('yesterday', bounds)).toEqual({
      startTs: dayStart - DAY,
      endTs: dayStart - 1,
    });
  });

  it('yesterday floors at minTs when the previous day starts before it', () => {
    const tightBounds = { minTs: bounds.maxTs - 12 * 3600, maxTs: bounds.maxTs };
    const dayStart = Math.floor(tightBounds.maxTs / DAY) * DAY;
    const result = resolveTimeRange('yesterday', tightBounds);
    expect(result.startTs).toBe(Math.max(tightBounds.minTs, dayStart - DAY));
    expect(result.endTs).toBe(dayStart - 1);
  });

  it('last7 clamps to 7 days before maxTs, floored at minTs', () => {
    expect(resolveTimeRange('last7', bounds)).toEqual({
      startTs: bounds.maxTs - 7 * DAY,
      endTs: bounds.maxTs,
    });
  });

  it('last30 clamps to 30 days before maxTs', () => {
    expect(resolveTimeRange('last30', bounds)).toEqual({
      startTs: bounds.maxTs - 30 * DAY,
      endTs: bounds.maxTs,
    });
  });

  it('last90 floors at minTs when the window would go before it', () => {
    const tightBounds = { minTs: 1_700_000_000, maxTs: 1_700_000_000 + 10 * DAY };
    expect(resolveTimeRange('last90', tightBounds)).toEqual({
      startTs: tightBounds.minTs,
      endTs: tightBounds.maxTs,
    });
  });

  it('all spans the full bounds', () => {
    expect(resolveTimeRange('all', bounds)).toEqual({ startTs: bounds.minTs, endTs: bounds.maxTs });
  });

  it('custom uses the given range, clamped to bounds', () => {
    const custom = { startTs: bounds.minTs + 5 * DAY, endTs: bounds.minTs + 20 * DAY };
    expect(resolveTimeRange('custom', bounds, custom)).toEqual(custom);
  });

  it('custom clamps a range that extends outside bounds', () => {
    const custom = { startTs: bounds.minTs - 10 * DAY, endTs: bounds.maxTs + 10 * DAY };
    expect(resolveTimeRange('custom', bounds, custom)).toEqual({ startTs: bounds.minTs, endTs: bounds.maxTs });
  });

  it('throws if custom is selected without a custom range', () => {
    expect(() => resolveTimeRange('custom', bounds)).toThrow();
  });
});
