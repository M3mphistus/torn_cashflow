export type TimeRangePreset = 'last7' | 'last30' | 'last90' | 'custom' | 'all';

export interface TimeRangeBounds {
  minTs: number;
  maxTs: number;
}

export interface ResolvedRange {
  startTs: number;
  endTs: number;
}

const DAY_SECONDS = 86400;

export function resolveTimeRange(
  preset: TimeRangePreset,
  bounds: TimeRangeBounds,
  custom?: ResolvedRange,
): ResolvedRange {
  const { minTs, maxTs } = bounds;

  if (preset === 'custom') {
    if (!custom) throw new Error('custom preset requires a custom range');
    return {
      startTs: Math.max(minTs, custom.startTs),
      endTs: Math.min(maxTs, custom.endTs),
    };
  }

  const endTs = maxTs;
  let startTs: number;
  switch (preset) {
    case 'last7':
      startTs = Math.max(minTs, endTs - 7 * DAY_SECONDS);
      break;
    case 'last30':
      startTs = Math.max(minTs, endTs - 30 * DAY_SECONDS);
      break;
    case 'last90':
      startTs = Math.max(minTs, endTs - 90 * DAY_SECONDS);
      break;
    case 'all':
      startTs = minTs;
      break;
  }
  return { startTs, endTs };
}
