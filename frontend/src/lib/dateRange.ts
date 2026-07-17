export type TimeRangePreset = 'today' | 'yesterday' | 'last7' | 'last30' | 'last90' | 'custom' | 'all';

export interface TimeRangeBounds {
  minTs: number;
  maxTs: number;
}

export interface ResolvedRange {
  startTs: number;
  endTs: number;
}

const DAY_SECONDS = 86400;

function startOfUtcDay(ts: number): number {
  return Math.floor(ts / DAY_SECONDS) * DAY_SECONDS;
}

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

  // "Today"/"yesterday" anchor to the calendar day of maxTs (the latest data point), not the
  // browser's current date - if the last sync was a while ago, real "today" would otherwise be
  // an empty range even though the data itself is fine, which reads as "broken" to a user.
  if (preset === 'today') {
    const dayStart = startOfUtcDay(maxTs);
    return { startTs: Math.max(minTs, dayStart), endTs: Math.min(maxTs, dayStart + DAY_SECONDS - 1) };
  }
  if (preset === 'yesterday') {
    const todayStart = startOfUtcDay(maxTs);
    return { startTs: Math.max(minTs, todayStart - DAY_SECONDS), endTs: Math.min(maxTs, todayStart - 1) };
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
