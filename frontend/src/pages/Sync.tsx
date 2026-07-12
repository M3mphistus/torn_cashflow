import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { syncIncremental, startFullHistorySync, getFullHistoryJob } from '../api/sync';
import { getLatestSnapshot, updateSnapshotNote } from '../api/snapshots';
import { getUncategorizedEntries, getIgnoredEntries, updateLogEntry, ignoreLogEntry, restoreLogEntry } from '../api/logEntries';
import { getCategories } from '../api/categories';
import { clearAllData } from '../api/data';
import { ApiError } from '../api/client';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { formatTimestamp, formatCurrency } from '../lib/format';
import type { LogEntryDTO } from '../types/api';

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

export default function SyncPage() {
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

  const latestSnapshotQuery = useQuery({ queryKey: ['snapshots', 'latest'], queryFn: getLatestSnapshot });
  const latest = latestSnapshotQuery.data?.snapshot ?? null;
  const [noteDraft, setNoteDraft] = useState<string | null>(null);
  const noteMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) => updateSnapshotNote(id, note),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['snapshots'] }),
  });

  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories });
  const categoryOptions = [...(categoriesQuery.data?.categories.map((c) => c.name) ?? []), 'Uncategorized'];

  const uncategorizedQuery = useQuery({ queryKey: ['log-entries', 'uncategorized'], queryFn: () => getUncategorizedEntries(25) });
  const ignoredQuery = useQuery({ queryKey: ['log-entries', 'ignored'], queryFn: () => getIgnoredEntries(25) });

  const saveEntryMutation = useMutation({
    mutationFn: ({ id, category, note }: { id: number; category: string; note: string }) => updateLogEntry(id, category, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });
  const ignoreEntryMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) => ignoreLogEntry(id, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });
  const restoreEntryMutation = useMutation({
    mutationFn: (id: number) => restoreLogEntry(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['log-entries'] }),
  });

  const [confirmClear, setConfirmClear] = useState(false);
  const clearMutation = useMutation({
    mutationFn: clearAllData,
    onSuccess: () => {
      setConfirmClear(false);
      queryClient.invalidateQueries();
    },
  });

  return (
    <div className="page">
      <h1>Sync</h1>

      {latest ? <p>Last sync: {formatTimestamp(latest.syncedAt)}</p> : <p>No sync has happened yet.</p>}

      <div style={{ margin: '16px 0' }}>
        <Button variant="primary" onClick={() => incrementalMutation.mutate()} disabled={incrementalMutation.isPending}>
          {incrementalMutation.isPending ? 'Syncing…' : 'Sync now'}
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

      <hr />
      <SectionHeading premium>Full History Sync</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Fetches your current bars/money/stats plus your complete log history by paging backward
        through the Torn API, bypassing its ~100-entries-per-call cap. This uses many API requests
        and can take a while for accounts with a long history.
      </p>
      {!premium?.isPremium && (
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
          Requires Premium — clicking below will show your options (trial, Xanax payment, or faction bulk).
        </p>
      )}

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

      {attemptedWithoutPremium && !premium?.isPremium && (
        <AlertBanner kind="warning">
          Full History Sync is a Premium feature. Start your free trial, pay with Xanax, or check
          faction options on the Settings page.
        </AlertBanner>
      )}

      {fullHistoryJobId !== null && fullHistoryJob.data && (
        <AlertBanner kind={fullHistoryJob.data.status === 'failed' ? 'error' : 'info'}>
          {fullHistoryJob.data.status === 'running' && (
            <>
              Page {fullHistoryJob.data.pagesFetched}: {fullHistoryJob.data.entriesFetched} log entries
              fetched so far
              {fullHistoryJob.data.oldestTimestamp && ` (oldest so far: ${formatTimestamp(fullHistoryJob.data.oldestTimestamp)})`}…
              {fullHistoryJob.isStalled && ' This looks stalled — you can retry below.'}
            </>
          )}
          {fullHistoryJob.data.status === 'completed' && fullHistoryJob.data.result && (
            <>
              Full history sync complete. {fullHistoryJob.data.result.newEntriesStored} new log
              entries ({fullHistoryJob.data.result.alreadyStored} were already stored).
            </>
          )}
          {fullHistoryJob.data.status === 'failed' && <>Full history sync failed: {fullHistoryJob.data.error}</>}
        </AlertBanner>
      )}
      {fullHistoryJob.isStalled && <Button onClick={() => startFullHistoryMutation.mutate()}>Retry</Button>}

      <hr />
      <SectionHeading>Period Note</SectionHeading>
      {latest && (
        <div style={{ maxWidth: 480 }}>
          <label htmlFor="period-note">Note for the latest sync period</label>
          <textarea id="period-note" value={noteDraft ?? latest.note ?? ''} onChange={(e) => setNoteDraft(e.target.value)} rows={3} />
          <div style={{ marginTop: 8 }}>
            <Button
              onClick={() => noteMutation.mutate({ id: latest.id, note: noteDraft ?? latest.note ?? '' })}
              disabled={noteMutation.isPending}
            >
              Save note
            </Button>
          </div>
          {noteMutation.isSuccess && <AlertBanner kind="success">Note saved.</AlertBanner>}
          {noteMutation.isError && (
            <AlertBanner kind="error">
              {noteMutation.error instanceof ApiError ? noteMutation.error.message : 'Failed to save note.'}
            </AlertBanner>
          )}
        </div>
      )}

      <hr />
      <SectionHeading>Uncategorized Log Entries</SectionHeading>
      {saveEntryMutation.isError && (
        <AlertBanner kind="error">
          {saveEntryMutation.error instanceof ApiError ? saveEntryMutation.error.message : 'Failed to save entry.'}
        </AlertBanner>
      )}
      {ignoreEntryMutation.isError && (
        <AlertBanner kind="error">
          {ignoreEntryMutation.error instanceof ApiError ? ignoreEntryMutation.error.message : 'Failed to ignore entry.'}
        </AlertBanner>
      )}
      {!uncategorizedQuery.data || uncategorizedQuery.data.entries.length === 0 ? (
        <AlertBanner kind="info">No uncategorized log entries.</AlertBanner>
      ) : (
        <>
          {uncategorizedQuery.data.totalCount > uncategorizedQuery.data.entries.length && (
            <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
              Showing the {uncategorizedQuery.data.entries.length} most recent of{' '}
              {uncategorizedQuery.data.totalCount} uncategorized entries. Use the Categories page to
              bulk-recategorize the rest by title.
            </p>
          )}
          {uncategorizedQuery.data.entries.map((entry) => (
            <UncategorizedEntryRow
              key={entry.id}
              entry={entry}
              categoryOptions={categoryOptions}
              onSave={(category, note) => saveEntryMutation.mutate({ id: entry.id, category, note })}
              onIgnore={(note) => ignoreEntryMutation.mutate({ id: entry.id, note })}
            />
          ))}
        </>
      )}

      <hr />
      <SectionHeading>Ignored Log Entries</SectionHeading>
      {restoreEntryMutation.isError && (
        <AlertBanner kind="error">
          {restoreEntryMutation.error instanceof ApiError ? restoreEntryMutation.error.message : 'Failed to restore entry.'}
        </AlertBanner>
      )}
      {!ignoredQuery.data || ignoredQuery.data.entries.length === 0 ? (
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>No ignored log entries.</p>
      ) : (
        <details>
          <summary>
            {ignoredQuery.data.entries.length} most recent of {ignoredQuery.data.totalCount} ignored entries
          </summary>
          {ignoredQuery.data.entries.map((entry) => (
            <div key={entry.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' }}>
              <span>
                <strong>{entry.title || 'Unknown event'}</strong> — {formatTimestamp(entry.timestamp)}
              </span>
              <Button onClick={() => restoreEntryMutation.mutate(entry.id)}>Restore</Button>
            </div>
          ))}
        </details>
      )}

      <hr />
      <SectionHeading>Danger Zone</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Deletes all your synced snapshots, log entries, and learned category rules from the
        database. Your checklist tasks and War Mode setting are not affected. This cannot be
        undone.
      </p>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, textTransform: 'none' }}>
        <input type="checkbox" style={{ width: 'auto' }} checked={confirmClear} onChange={(e) => setConfirmClear(e.target.checked)} />
        I understand this permanently deletes all synced data
      </label>
      <div style={{ marginTop: 8 }}>
        <Button variant="danger" disabled={!confirmClear || clearMutation.isPending} onClick={() => clearMutation.mutate()}>
          Clear DB
        </Button>
      </div>
      {clearMutation.isSuccess && <AlertBanner kind="success">All synced data cleared.</AlertBanner>}
    </div>
  );
}

function UncategorizedEntryRow({
  entry,
  categoryOptions,
  onSave,
  onIgnore,
}: {
  entry: LogEntryDTO;
  categoryOptions: string[];
  onSave: (category: string, note: string) => void;
  onIgnore: (note: string) => void;
}) {
  const [category, setCategory] = useState('Uncategorized');
  const [note, setNote] = useState(entry.userNote ?? '');

  return (
    <Card>
      <p>
        <strong>{entry.title || 'Unknown event'}</strong> — {formatTimestamp(entry.timestamp)} —{' '}
        {entry.amount !== null ? formatCurrency(entry.amount) : 'no amount detected'}
      </p>
      {entry.rawText && <p style={{ color: 'var(--text-dim)', fontSize: 12 }}>{entry.rawText}</p>}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div style={{ flex: '1 1 160px' }}>
          <label htmlFor={`cat-${entry.id}`}>Category</label>
          <select id={`cat-${entry.id}`} value={category} onChange={(e) => setCategory(e.target.value)}>
            {categoryOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: '1 1 160px' }}>
          <label htmlFor={`note-${entry.id}`}>Note</label>
          <input id={`note-${entry.id}`} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <Button onClick={() => onSave(category, note)}>Save</Button>
        <Button onClick={() => onIgnore(note)}>Ignore</Button>
      </div>
    </Card>
  );
}
