import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useAuth } from '../hooks/useAuth';
import { getDashboard, getDashboardBounds } from '../api/dashboard';
import { syncIncremental, startFullHistorySync, getFullHistoryJob } from '../api/sync';
import { ApiError } from '../api/client';
import KpiCard from '../components/ui/KpiCard';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import { formatCurrency, formatTimestamp } from '../lib/format';
import { resolveTimeRange, type TimeRangePreset } from '../lib/dateRange';
import { snapshotsToCsv, downloadCsv } from '../lib/csv';
import type { SnapshotDTO } from '../types/api';

function useFullHistoryJob(jobId: number | null) {
  const [lastProgressKey, setLastProgressKey] = useState('');
  const [lastProgressAt, setLastProgressAt] = useState(Date.now());

  const query = useQuery({
    queryKey: ['syncJob', jobId],
    queryFn: () => getFullHistoryJob(jobId as number),
    enabled: jobId !== null,
    refetchInterval: (q) => (q.state.data?.status === 'running' ? 2500 : false),
  });

  useEffect(() => {
    if (!query.data) return;
    const key = `${query.data.pagesFetched}-${query.data.entriesFetched}`;
    if (key !== lastProgressKey) {
      setLastProgressKey(key);
      setLastProgressAt(Date.now());
    }
  }, [query.data, lastProgressKey]);

  const isStalled = query.data?.status === 'running' && Date.now() - lastProgressAt > 60000;
  return { ...query, isStalled };
}

const PRESETS: { value: TimeRangePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
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
const chartTooltipLabelStyle = { color: 'var(--text-mute)' };
const chartTooltipItemStyle = { color: 'var(--text)' };
const chartTooltipCursor = { fill: 'var(--gold)', fillOpacity: 0.08 };

export default function DashboardPage() {
  const [preset, setPreset] = useState<TimeRangePreset>('last30');
  const [customStart, setCustomStart] = useState<string | null>(null);
  const [customEnd, setCustomEnd] = useState<string | null>(null);
  const [tab, setTab] = useState<'cashflow' | 'networth'>('cashflow');

  const boundsQuery = useQuery({ queryKey: ['dashboard', 'bounds'], queryFn: getDashboardBounds });

  const bounds = useMemo(() => {
    const { minTs, maxTs } = boundsQuery.data ?? {};
    if (minTs == null || maxTs == null) return null;
    return { minTs, maxTs };
  }, [boundsQuery.data]);

  const range = useMemo(() => {
    if (!bounds) return null;
    if (preset === 'custom') {
      const startTs = customStart ? fromDateInputValue(customStart, false) : bounds.minTs;
      const endTs = customEnd ? fromDateInputValue(customEnd, true) : bounds.maxTs;
      return resolveTimeRange('custom', bounds, { startTs, endTs });
    }
    return resolveTimeRange(preset, bounds);
  }, [preset, bounds, customStart, customEnd]);

  const dashboardQuery = useQuery({
    queryKey: ['dashboard', range?.startTs, range?.endTs],
    queryFn: () => getDashboard(range!.startTs, range!.endTs),
    enabled: range !== null,
  });

  const { premium } = useAuth();
  const queryClient = useQueryClient();

  const incrementalMutation = useMutation({
    mutationFn: syncIncremental,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snapshots'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });

  const [fullHistoryJobId, setFullHistoryJobId] = useState<number | null>(null);
  const [attemptedWithoutPremium, setAttemptedWithoutPremium] = useState(false);
  const startFullHistoryMutation = useMutation({
    mutationFn: startFullHistorySync,
    onSuccess: (data) => setFullHistoryJobId(data.jobId),
  });
  const fullHistoryJob = useFullHistoryJob(fullHistoryJobId);

  useEffect(() => {
    if (fullHistoryJob.data?.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['snapshots'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    }
  }, [fullHistoryJob.data?.status, queryClient]);

  const syncControls = (
    <>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', margin: '16px 0' }}>
        <Button variant="primary" onClick={() => incrementalMutation.mutate()} disabled={incrementalMutation.isPending}>
          {incrementalMutation.isPending ? 'Syncing…' : 'Sync now'}
        </Button>
        <Button
          onClick={() => {
            if (!premium?.isPremium) {
              setAttemptedWithoutPremium(true);
              return;
            }
            startFullHistoryMutation.mutate();
          }}
          disabled={startFullHistoryMutation.isPending || fullHistoryJob.data?.status === 'running'}
        >
          Get all Data
        </Button>
      </div>

      {incrementalMutation.isSuccess && (
        <AlertBanner kind="success">
          Sync complete. Stored 1 snapshot and {incrementalMutation.data.logEntriesStored} log entries.
          {incrementalMutation.data.paymentMessage && <> {incrementalMutation.data.paymentMessage}</>}
        </AlertBanner>
      )}
      {incrementalMutation.isError && (
        <AlertBanner kind="error">
          {incrementalMutation.error instanceof ApiError ? incrementalMutation.error.message : 'Sync failed.'}
        </AlertBanner>
      )}
      {attemptedWithoutPremium && !premium?.isPremium && (
        <AlertBanner kind="warning">
          Full History Sync is a Premium feature. Start your free trial, pay with Xanax, or check faction options on the Settings page.
        </AlertBanner>
      )}
      {fullHistoryJobId !== null && fullHistoryJob.data && (
        <AlertBanner kind={fullHistoryJob.data.status === 'failed' ? 'error' : 'info'}>
          {fullHistoryJob.data.status === 'running' && (
            <>
              Page {fullHistoryJob.data.pagesFetched}: {fullHistoryJob.data.entriesFetched} log entries fetched so
              far
              {fullHistoryJob.data.oldestTimestamp && ` (oldest so far: ${formatTimestamp(fullHistoryJob.data.oldestTimestamp)})`}…
              {fullHistoryJob.isStalled && ' This looks stalled — you can retry below.'}
            </>
          )}
          {fullHistoryJob.data.status === 'completed' && fullHistoryJob.data.result && (
            <>
              Full history sync complete. {fullHistoryJob.data.result.newEntriesStored} new log entries (
              {fullHistoryJob.data.result.alreadyStored} were already stored).
            </>
          )}
          {fullHistoryJob.data.status === 'failed' && <>Full history sync failed: {fullHistoryJob.data.error}</>}
        </AlertBanner>
      )}
      {fullHistoryJob.isStalled && <Button onClick={() => startFullHistoryMutation.mutate()}>Retry</Button>}
    </>
  );

  if (boundsQuery.isLoading) {
    return (
      <div className="page">
        <h1>Dashboard</h1>
        <p>Loading…</p>
      </div>
    );
  }

  if (bounds === null) {
    return (
      <div className="page">
        <h1>Dashboard</h1>
        {syncControls}
        <AlertBanner kind="info">Need at least one synced snapshot — click "Sync now" above.</AlertBanner>
      </div>
    );
  }

  const dashboard = dashboardQuery.data;
  const snapshotColumns = dashboard && dashboard.snapshots.length > 0 ? (Object.keys(dashboard.snapshots[0]) as (keyof SnapshotDTO)[]) : [];
  const sortedCategoryBreakdown = dashboard ? [...dashboard.categoryBreakdown].sort((a, b) => a.amount - b.amount) : [];

  return (
    <div className="page">
      <h1>Dashboard</h1>

      {syncControls}
      <hr />

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
              <BarChart data={sortedCategoryBreakdown} layout="vertical">
                <CartesianGrid stroke="var(--line)" horizontal={false} />
                <XAxis type="number" stroke="var(--text-mute)" tickFormatter={(v: number) => formatCurrency(v)} />
                <YAxis type="category" dataKey="category" stroke="var(--text-mute)" width={140} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} labelStyle={chartTooltipLabelStyle} itemStyle={chartTooltipItemStyle} cursor={chartTooltipCursor} />
                <Bar dataKey="amount">
                  {sortedCategoryBreakdown.map((row) => (
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
                  <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} labelStyle={chartTooltipLabelStyle} itemStyle={chartTooltipItemStyle} cursor={chartTooltipCursor} />
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
                <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} labelStyle={chartTooltipLabelStyle} itemStyle={chartTooltipItemStyle} />
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
