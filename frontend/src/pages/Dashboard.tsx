import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getDashboard } from '../api/dashboard';
import { getSnapshots } from '../api/snapshots';
import KpiCard from '../components/ui/KpiCard';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import { formatCurrency, formatTimestamp } from '../lib/format';
import { resolveTimeRange, type TimeRangePreset } from '../lib/dateRange';
import { snapshotsToCsv, downloadCsv } from '../lib/csv';
import type { SnapshotDTO } from '../types/api';

const PRESETS: { value: TimeRangePreset; label: string }[] = [
  { value: 'last7', label: 'Last 7 days' },
  { value: 'last30', label: 'Last 30 days' },
  { value: 'last90', label: 'Last 90 days' },
  { value: 'custom', label: 'Custom' },
  { value: 'all', label: 'All time' },
];

function toDateInputValue(ts: number): string {
  return new Date(ts * 1000).toISOString().slice(0, 10);
}

function fromDateInputValue(value: string, endOfDay: boolean): number {
  const ms = Date.parse(`${value}T${endOfDay ? '23:59:59' : '00:00:00'}Z`);
  return Math.floor(ms / 1000);
}

const chartTooltipStyle = { background: 'var(--panel-2)', border: '1px solid var(--line-lit)' };

export default function DashboardPage() {
  const [preset, setPreset] = useState<TimeRangePreset>('last30');
  const [customStart, setCustomStart] = useState<string | null>(null);
  const [customEnd, setCustomEnd] = useState<string | null>(null);
  const [tab, setTab] = useState<'cashflow' | 'networth'>('cashflow');

  const boundsQuery = useQuery({ queryKey: ['snapshots', 'all'], queryFn: () => getSnapshots() });
  const snapshots = boundsQuery.data?.snapshots ?? [];

  const bounds = useMemo(() => {
    if (snapshots.length === 0) return null;
    return { minTs: snapshots[0].syncedAt, maxTs: snapshots[snapshots.length - 1].syncedAt };
  }, [snapshots]);

  const range = useMemo(() => {
    if (!bounds) return null;
    if (preset === 'custom') {
      if (!customStart || !customEnd) return null;
      return resolveTimeRange('custom', bounds, {
        startTs: fromDateInputValue(customStart, false),
        endTs: fromDateInputValue(customEnd, true),
      });
    }
    return resolveTimeRange(preset, bounds);
  }, [preset, bounds, customStart, customEnd]);

  const dashboardQuery = useQuery({
    queryKey: ['dashboard', range?.startTs, range?.endTs],
    queryFn: () => getDashboard(range!.startTs, range!.endTs),
    enabled: range !== null,
  });

  if (boundsQuery.isLoading) {
    return (
      <div className="page">
        <h1>Dashboard</h1>
        <p>Loading…</p>
      </div>
    );
  }

  if (snapshots.length === 0) {
    return (
      <div className="page">
        <h1>Dashboard</h1>
        <AlertBanner kind="info">Need at least one synced snapshot. Go to Sync first.</AlertBanner>
      </div>
    );
  }

  const dashboard = dashboardQuery.data;
  const snapshotColumns = dashboard && dashboard.snapshots.length > 0 ? (Object.keys(dashboard.snapshots[0]) as (keyof SnapshotDTO)[]) : [];

  return (
    <div className="page">
      <h1>Dashboard</h1>

      <div className="tabs" role="tablist" aria-label="Time range">
        {PRESETS.map((p) => (
          <button key={p.value} className={preset === p.value ? 'active' : ''} onClick={() => setPreset(p.value)}>
            {p.label}
          </button>
        ))}
      </div>

      {preset === 'custom' && bounds && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <div>
            <label htmlFor="custom-start">Start date</label>
            <input
              id="custom-start"
              type="date"
              min={toDateInputValue(bounds.minTs)}
              max={toDateInputValue(bounds.maxTs)}
              value={customStart ?? toDateInputValue(bounds.minTs)}
              onChange={(e) => setCustomStart(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="custom-end">End date</label>
            <input
              id="custom-end"
              type="date"
              min={toDateInputValue(bounds.minTs)}
              max={toDateInputValue(bounds.maxTs)}
              value={customEnd ?? toDateInputValue(bounds.maxTs)}
              onChange={(e) => setCustomEnd(e.target.value)}
            />
          </div>
        </div>
      )}

      {!dashboard ? (
        <p>Loading…</p>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
            <KpiCard label="Total Cashflow" value={formatCurrency(dashboard.cashflowTotal)} />
            <KpiCard label="Cashflow / Day" value={formatCurrency(dashboard.cashflowPerDay)} />
          </div>

          <hr />
          <SectionHeading>Cashflow by Category</SectionHeading>
          {dashboard.categoryBreakdown.length === 0 ? (
            <AlertBanner kind="info">No categorized log data in this range yet.</AlertBanner>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(200, dashboard.categoryBreakdown.length * 36)}>
              <BarChart data={[...dashboard.categoryBreakdown].sort((a, b) => a.amount - b.amount)} layout="vertical">
                <CartesianGrid stroke="var(--line)" horizontal={false} />
                <XAxis type="number" stroke="var(--text-mute)" tickFormatter={(v: number) => formatCurrency(v)} />
                <YAxis type="category" dataKey="category" stroke="var(--text-mute)" width={140} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} />
                <Bar dataKey="amount">
                  {dashboard.categoryBreakdown.map((row) => (
                    <Cell key={row.category} fill={row.amount >= 0 ? 'var(--gold)' : 'var(--red)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}

          <hr />
          <SectionHeading>Networth Breakdown</SectionHeading>
          <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
            As of the latest sync in the selected time range. "Trade" isn't exposed by the Torn API
            and is shown as n/a. This reflects Torn's own networth figure, which Torn recalculates
            roughly once a day — not a live estimate, so it can lag behind other tools that compute
            it more frequently.
          </p>
          <table>
            <thead>
              <tr>
                <th>Component</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.networthBreakdown.map((row) => (
                <tr key={row.component}>
                  <td>{row.component}</td>
                  <td>{formatCurrency(row.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <hr />
          <SectionHeading>Time Series</SectionHeading>
          <div className="tabs">
            <button className={tab === 'cashflow' ? 'active' : ''} onClick={() => setTab('cashflow')}>
              Cashflow / Day
            </button>
            <button className={tab === 'networth' ? 'active' : ''} onClick={() => setTab('networth')}>
              Networth
            </button>
          </div>
          {tab === 'cashflow' ? (
            dashboard.dailyCashflow.length === 0 ? (
              <AlertBanner kind="info">No categorized cashflow entries in this range yet.</AlertBanner>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={dashboard.dailyCashflow}>
                  <CartesianGrid stroke="var(--line)" />
                  <XAxis dataKey="date" stroke="var(--text-mute)" />
                  <YAxis stroke="var(--text-mute)" tickFormatter={(v: number) => formatCurrency(v)} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} />
                  <Bar dataKey="cashflowDelta" fill="var(--gold)" />
                </BarChart>
              </ResponsiveContainer>
            )
          ) : dashboard.dailyNetworth.length === 0 ? (
            <AlertBanner kind="info">No synced data in this range yet.</AlertBanner>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={dashboard.dailyNetworth}>
                <CartesianGrid stroke="var(--line)" />
                <XAxis dataKey="date" stroke="var(--text-mute)" />
                <YAxis stroke="var(--text-mute)" tickFormatter={(v: number) => formatCurrency(v)} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} />
                <Line type="monotone" dataKey="networth" stroke="var(--gold-bright)" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}

          <hr />
          <SectionHeading>Raw Snapshots</SectionHeading>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  {snapshotColumns.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dashboard.snapshots.map((s) => (
                  <tr key={s.id}>
                    {snapshotColumns.map((c) => (
                      <td key={c}>{c === 'syncedAt' ? formatTimestamp(s.syncedAt) : String(s[c] ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 12 }}>
            <Button onClick={() => downloadCsv('torn_snapshots.csv', snapshotsToCsv(dashboard.snapshots))}>Export CSV</Button>
          </div>
        </>
      )}
    </div>
  );
}
