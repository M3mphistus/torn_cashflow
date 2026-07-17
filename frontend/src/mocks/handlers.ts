import { delay, http, HttpResponse } from 'msw';
import {
  makeSnapshot,
  mockCategories,
  mockChecklistTasks,
  mockLifetimeGrants,
  mockLogEntries,
  mockPlayer,
  mockPremium,
  mockSession,
  mockSnapshots,
  mockWarMode,
} from './data';
import type { ChecklistTaskDTO, FullHistoryJobDTO, LogEntryDTO, SnapshotDTO } from '../types/api';

function errorBody(message: string, code: string, tornErrorCode: number | null = null) {
  return { error: { message, code, tornErrorCode } };
}

let nextChecklistId = 100;
let nextLogEntryId = 100;
let nextJobId = 1;
const fullHistoryJobs = new Map<number, FullHistoryJobDTO>();

function categoryCount(name: string): number {
  return mockLogEntries.filter((e) => e.appCategory === name).length;
}

function simulateFullHistoryProgress(job: FullHistoryJobDTO): void {
  let tick = 0;
  const interval = setInterval(() => {
    tick += 1;
    if (tick <= 4) {
      job.pagesFetched = tick;
      job.entriesFetched = tick * 300;
      job.oldestTimestamp = Math.floor(Date.now() / 1000) - tick * 30 * 86400;
    } else {
      job.status = 'completed';
      job.result = { newEntriesStored: 1180, alreadyStored: 40 };
      clearInterval(interval);
    }
  }, 1200);
}

export const handlers = [
  http.get('/api/auth/me', async () => {
    await delay(800);
    if (!mockSession.loggedIn) {
      return HttpResponse.json(errorBody('Not signed in.', 'not_authenticated'), { status: 401 });
    }
    return HttpResponse.json({ player: mockPlayer, premium: mockPremium });
  }),

  http.post('/api/auth/login', async ({ request }) => {
    const body = (await request.json()) as { apiKey: string };
    if (!body.apiKey || !body.apiKey.trim()) {
      return HttpResponse.json(errorBody('Enter a key before saving.', 'invalid_request'), { status: 400 });
    }
    if (body.apiKey.trim() === 'invalid') {
      return HttpResponse.json(errorBody('Incorrect API key.', 'invalid_key', 2), { status: 401 });
    }
    mockSession.loggedIn = true;
    return HttpResponse.json({ player: mockPlayer, premium: mockPremium });
  }),

  http.post('/api/auth/logout', () => {
    mockSession.loggedIn = false;
    return new HttpResponse(null, { status: 204 });
  }),

  http.get('/api/snapshots', ({ request }) => {
    const url = new URL(request.url);
    const startTs = url.searchParams.get('startTs');
    const endTs = url.searchParams.get('endTs');
    let rows = mockSnapshots;
    if (startTs) rows = rows.filter((s) => s.syncedAt >= Number(startTs));
    if (endTs) rows = rows.filter((s) => s.syncedAt <= Number(endTs));
    return HttpResponse.json({ snapshots: rows });
  }),

  http.get('/api/snapshots/latest', () => {
    const snapshot = mockSnapshots.length ? mockSnapshots[mockSnapshots.length - 1] : null;
    return HttpResponse.json({ snapshot });
  }),

  http.patch('/api/snapshots/:id/note', async ({ params, request }) => {
    const { note } = (await request.json()) as { note: string };
    const snapshot = mockSnapshots.find((s) => s.id === Number(params.id));
    if (!snapshot) return HttpResponse.json(errorBody('Snapshot not found.', 'not_found'), { status: 404 });
    snapshot.note = note;
    return HttpResponse.json({ snapshot });
  }),

  http.get('/api/dashboard/bounds', () => {
    const timestamps = [...mockSnapshots.map((s) => s.syncedAt), ...mockLogEntries.map((e) => e.timestamp)];
    if (timestamps.length === 0) return HttpResponse.json({ minTs: null, maxTs: null });
    return HttpResponse.json({ minTs: Math.min(...timestamps), maxTs: Math.max(...timestamps) });
  }),

  http.get('/api/dashboard', ({ request }) => {
    const url = new URL(request.url);
    const startTs = Number(url.searchParams.get('startTs'));
    const endTs = Number(url.searchParams.get('endTs'));
    const snapshots = mockSnapshots.filter((s) => s.syncedAt >= startTs && s.syncedAt <= endTs);
    const entries = mockLogEntries.filter((e) => e.timestamp >= startTs && e.timestamp <= endTs);
    const countable = entries.filter((e) => e.amount !== null && e.appCategory !== 'Ignored');
    const cashflowTotal = countable.reduce((sum, e) => sum + (e.amount ?? 0), 0);
    const days = Math.max((endTs - startTs) / 86400, 1);
    const cashflowPerDay = cashflowTotal / days;

    const byCategory = new Map<string, number>();
    for (const e of countable) {
      byCategory.set(e.appCategory, (byCategory.get(e.appCategory) ?? 0) + (e.amount ?? 0));
    }

    const latest = snapshots[snapshots.length - 1] ?? mockSnapshots[mockSnapshots.length - 1];
    const networthBreakdown = [
      { component: 'Networth Total', amount: latest.networth },
      { component: 'Pending', amount: latest.nwPending },
      { component: 'Wallet', amount: latest.nwWallet },
      { component: 'Bank', amount: latest.nwBank },
      { component: 'Points @ $', amount: latest.nwPoints },
      { component: 'Cayman', amount: latest.nwCayman },
      { component: 'Vault', amount: latest.nwVault },
      { component: 'Piggy Bank', amount: latest.nwPiggybank },
      { component: 'Items', amount: latest.nwItems },
      { component: 'Display Case', amount: latest.nwDisplaycase },
      { component: 'Bazaar', amount: latest.nwBazaar },
      { component: 'Trade', amount: null },
      { component: 'Items Market', amount: latest.nwItemmarket },
      { component: 'Properties', amount: latest.nwProperties },
      { component: 'Stock Market', amount: latest.nwStockmarket },
      { component: 'Auction House', amount: latest.nwAuctionhouse },
      { component: 'Company', amount: latest.nwCompany },
      { component: 'Bookie', amount: latest.nwBookie },
      { component: 'Enlisted Cars', amount: latest.nwEnlistedcars },
      { component: 'Loan', amount: latest.nwLoan },
      { component: 'Unpaid Fees', amount: latest.nwUnpaidfees },
    ];

    const dailyCashflowMap = new Map<string, number>();
    for (const e of countable) {
      const date = new Date(e.timestamp * 1000).toISOString().slice(0, 10);
      dailyCashflowMap.set(date, (dailyCashflowMap.get(date) ?? 0) + (e.amount ?? 0));
    }
    const dailyNetworthMap = new Map<string, number>();
    for (const s of snapshots) {
      const date = new Date(s.syncedAt * 1000).toISOString().slice(0, 10);
      dailyNetworthMap.set(date, s.networth);
    }

    return HttpResponse.json({
      cashflowTotal,
      cashflowPerDay,
      categoryBreakdown: [...byCategory.entries()].map(([category, amount]) => ({ category, amount })),
      networthBreakdown,
      dailyCashflow: [...dailyCashflowMap.entries()].map(([date, cashflowDelta]) => ({ date, cashflowDelta })),
      dailyNetworth: [...dailyNetworthMap.entries()].map(([date, networth]) => ({ date, networth })),
      snapshots,
    });
  }),

  http.get('/api/log-entries/uncategorized', ({ request }) => {
    const limit = Number(new URL(request.url).searchParams.get('limit') ?? 25);
    const all = mockLogEntries.filter((e) => e.appCategory === 'Uncategorized');
    return HttpResponse.json({ entries: all.slice(0, limit), totalCount: all.length });
  }),

  http.get('/api/log-entries/ignored', ({ request }) => {
    const limit = Number(new URL(request.url).searchParams.get('limit') ?? 25);
    const all = mockLogEntries.filter((e) => e.appCategory === 'Ignored');
    return HttpResponse.json({ entries: all.slice(0, limit), totalCount: all.length });
  }),

  http.get('/api/log-entries', ({ request }) => {
    const category = new URL(request.url).searchParams.get('category');
    const rows = category ? mockLogEntries.filter((e) => e.appCategory === category) : mockLogEntries;
    return HttpResponse.json({ entries: rows });
  }),

  http.patch('/api/log-entries/:id', async ({ params, request }) => {
    const { appCategory, userNote } = (await request.json()) as { appCategory: string; userNote: string | null };
    const entry = mockLogEntries.find((e) => e.id === Number(params.id));
    if (!entry) return HttpResponse.json(errorBody('Entry not found.', 'not_found'), { status: 404 });
    entry.appCategory = appCategory;
    entry.userNote = userNote;
    let bulkUpdatedCount = 0;
    if (entry.title) {
      for (const other of mockLogEntries) {
        if (other.id !== entry.id && other.title === entry.title && other.appCategory === 'Uncategorized') {
          other.appCategory = appCategory;
          bulkUpdatedCount += 1;
        }
      }
    }
    return HttpResponse.json({ entry, bulkUpdatedCount });
  }),

  http.post('/api/log-entries/:id/ignore', async ({ params, request }) => {
    const { userNote } = (await request.json()) as { userNote: string | null };
    const entry = mockLogEntries.find((e) => e.id === Number(params.id));
    if (!entry) return HttpResponse.json(errorBody('Entry not found.', 'not_found'), { status: 404 });
    entry.appCategory = 'Ignored';
    entry.userNote = userNote;
    let bulkUpdatedCount = 0;
    if (entry.title) {
      for (const other of mockLogEntries) {
        if (other.id !== entry.id && other.title === entry.title && other.appCategory === 'Uncategorized') {
          other.appCategory = 'Ignored';
          bulkUpdatedCount += 1;
        }
      }
    }
    return HttpResponse.json({ entry, bulkUpdatedCount });
  }),

  http.post('/api/log-entries/:id/restore', ({ params }) => {
    const entry = mockLogEntries.find((e) => e.id === Number(params.id));
    if (!entry) return HttpResponse.json(errorBody('Entry not found.', 'not_found'), { status: 404 });
    entry.appCategory = 'Uncategorized';
    return HttpResponse.json({ entry });
  }),

  http.post('/api/log-entries/recategorize-period', async ({ request }) => {
    const { startTs, endTs, appCategory } = (await request.json()) as {
      startTs: number;
      endTs: number;
      appCategory: string;
    };
    let updatedCount = 0;
    for (const entry of mockLogEntries) {
      if (entry.timestamp >= startTs && entry.timestamp <= endTs) {
        entry.appCategory = appCategory;
        updatedCount += 1;
      }
    }
    return HttpResponse.json({ updatedCount });
  }),

  http.get('/api/categories', () => {
    return HttpResponse.json({ categories: mockCategories.map((name) => ({ name, entryCount: categoryCount(name) })) });
  }),

  http.post('/api/categories', async ({ request }) => {
    const { name } = (await request.json()) as { name: string };
    if (name === 'Uncategorized' || name === 'Ignored' || mockCategories.includes(name)) {
      return HttpResponse.json(errorBody(`'${name}' already exists or is reserved.`, 'category_conflict'), { status: 409 });
    }
    mockCategories.push(name);
    return HttpResponse.json({ name }, { status: 201 });
  }),

  http.delete('/api/categories/:name', ({ params }) => {
    const name = decodeURIComponent(params.name as string);
    if (categoryCount(name) > 0) {
      return HttpResponse.json(errorBody(`'${name}' is still used by log entries.`, 'category_in_use'), { status: 409 });
    }
    const index = mockCategories.indexOf(name);
    if (index !== -1) mockCategories.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.get('/api/categories/title-summary', ({ request }) => {
    const filter = new URL(request.url).searchParams.get('filterCategory');
    const byTitle = new Map<string, { title: string; category: string; entryCount: number }>();
    for (const entry of mockLogEntries) {
      if (filter && entry.appCategory !== filter) continue;
      const key = `${entry.title}::${entry.appCategory}`;
      const existing = byTitle.get(key);
      if (existing) existing.entryCount += 1;
      else byTitle.set(key, { title: entry.title, category: entry.appCategory, entryCount: 1 });
    }
    return HttpResponse.json({ rows: [...byTitle.values()] });
  }),

  http.post('/api/categories/reassign', async ({ request }) => {
    const { title, fromCategory, toCategory } = (await request.json()) as {
      title: string;
      fromCategory: string;
      toCategory: string;
    };
    let updatedCount = 0;
    for (const entry of mockLogEntries) {
      if (entry.title === title && entry.appCategory === fromCategory) {
        entry.appCategory = toCategory;
        updatedCount += 1;
      }
    }
    return HttpResponse.json({ updatedCount });
  }),

  http.post('/api/sync/incremental', async () => {
    await delay(500);
    const now = Math.floor(Date.now() / 1000);
    const base = mockSnapshots.length ? mockSnapshots[mockSnapshots.length - 1] : makeSnapshot(0);
    const snapshot: SnapshotDTO = { ...base, id: mockSnapshots.length + 1000, syncedAt: now, note: null };
    mockSnapshots.push(snapshot);
    const newEntry: LogEntryDTO = {
      id: nextLogEntryId++,
      tornLogId: String(900000 + nextLogEntryId),
      timestamp: now,
      category: 'Attacking',
      title: 'Attacked player Y',
      rawText: 'You attacked player Y and won, gaining $8,000',
      amount: 8000,
      appCategory: 'Ranked War',
      userNote: null,
    };
    mockLogEntries.push(newEntry);
    return HttpResponse.json({ snapshot, logEntriesStored: 1, paymentMessage: null });
  }),

  http.post('/api/sync/full-history', () => {
    const jobId = nextJobId++;
    const job: FullHistoryJobDTO = {
      jobId,
      status: 'running',
      pagesFetched: 0,
      entriesFetched: 0,
      oldestTimestamp: null,
      error: null,
      result: null,
    };
    fullHistoryJobs.set(jobId, job);
    simulateFullHistoryProgress(job);
    return HttpResponse.json({ jobId, status: 'running' }, { status: 202 });
  }),

  http.get('/api/sync/full-history/:jobId', ({ params }) => {
    const job = fullHistoryJobs.get(Number(params.jobId));
    if (!job) return HttpResponse.json(errorBody('Job not found.', 'not_found'), { status: 404 });
    return HttpResponse.json(job);
  }),

  http.get('/api/checklist', () => HttpResponse.json({ tasks: mockChecklistTasks })),

  http.post('/api/checklist', async ({ request }) => {
    const input = (await request.json()) as Omit<ChecklistTaskDTO, 'id' | 'createdAt' | 'lastCompletedAt' | 'isDoneCurrentCycle'>;
    const task: ChecklistTaskDTO = {
      id: nextChecklistId++,
      title: input.title,
      description: input.description || null,
      repeatType: input.repeatType,
      repeatIntervalDays: input.repeatType === 'every_x_days' ? input.repeatIntervalDays : null,
      createdAt: Math.floor(Date.now() / 1000),
      lastCompletedAt: null,
      isDoneCurrentCycle: false,
    };
    mockChecklistTasks.push(task);
    return HttpResponse.json({ task }, { status: 201 });
  }),

  http.patch('/api/checklist/:id', async ({ params, request }) => {
    const input = (await request.json()) as Omit<ChecklistTaskDTO, 'id' | 'createdAt' | 'lastCompletedAt' | 'isDoneCurrentCycle'>;
    const task = mockChecklistTasks.find((t) => t.id === Number(params.id));
    if (!task) return HttpResponse.json(errorBody('Task not found.', 'not_found'), { status: 404 });
    task.title = input.title;
    task.description = input.description || null;
    task.repeatType = input.repeatType;
    task.repeatIntervalDays = input.repeatType === 'every_x_days' ? input.repeatIntervalDays : null;
    return HttpResponse.json({ task });
  }),

  http.delete('/api/checklist/:id', ({ params }) => {
    const index = mockChecklistTasks.findIndex((t) => t.id === Number(params.id));
    if (index !== -1) mockChecklistTasks.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post('/api/checklist/:id/done', async ({ params, request }) => {
    const { done } = (await request.json()) as { done: boolean };
    const task = mockChecklistTasks.find((t) => t.id === Number(params.id));
    if (!task) return HttpResponse.json(errorBody('Task not found.', 'not_found'), { status: 404 });
    task.isDoneCurrentCycle = done;
    if (done) task.lastCompletedAt = Math.floor(Date.now() / 1000);
    return HttpResponse.json({ task });
  }),

  http.get('/api/settings/war-mode', () => HttpResponse.json(mockWarMode)),

  http.put('/api/settings/war-mode', async ({ request }) => {
    const { active } = (await request.json()) as { active: boolean };
    mockWarMode.active = active;
    if (active) mockWarMode.startedAt = Math.floor(Date.now() / 1000);
    return HttpResponse.json(mockWarMode);
  }),

  http.get('/api/licensing/status', () => HttpResponse.json({ ...mockPremium, trialUsed: mockSession.trialUsed })),

  http.post('/api/licensing/trial', () => {
    if (mockSession.trialUsed) {
      return HttpResponse.json({ started: false, reason: 'Trial already used.', premiumUntil: null });
    }
    mockSession.trialUsed = true;
    const premiumUntil = Math.floor(Date.now() / 1000) + 7 * 86400;
    mockPremium.isPremium = true;
    mockPremium.premiumUntil = premiumUntil;
    mockPremium.source = 'trial';
    return HttpResponse.json({ started: true, reason: null, premiumUntil });
  }),

  http.post('/api/licensing/scan-payment', () =>
    HttpResponse.json({ creditedCount: 0, weeksAdded: 0, newPremiumUntil: null, alreadyCreditedCount: 0 }),
  ),

  http.get('/api/licensing/faction-preview', () => {
    if (!mockPlayer.factionId) return new HttpResponse(null, { status: 204 });
    return HttpResponse.json({ memberCount: 34, lifetimeCoveredCount: 2, payableMembers: 32, discountPct: 0.1, required: 29 });
  }),

  http.post('/api/licensing/scan-group-payment', () =>
    HttpResponse.json({ activated: false, message: "Sent 0, need 29 for your faction's 34 members.", required: 29, sent: 0 }),
  ),

  http.get('/api/admin/lifetime-grants', () => HttpResponse.json({ grants: mockLifetimeGrants })),

  http.post('/api/admin/lifetime-grants', async ({ request }) => {
    const grant = (await request.json()) as { scope: 'individual' | 'faction'; key: number };
    mockLifetimeGrants.push({ ...grant, activatedAt: Math.floor(Date.now() / 1000) });
    return new HttpResponse(null, { status: 201 });
  }),

  http.delete('/api/admin/lifetime-grants', async ({ request }) => {
    const { scope, key } = (await request.json()) as { scope: 'individual' | 'faction'; key: number };
    const index = mockLifetimeGrants.findIndex((g) => g.scope === scope && g.key === key);
    if (index !== -1) mockLifetimeGrants.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.delete('/api/data', () => {
    mockSnapshots.length = 0;
    mockLogEntries.length = 0;
    return new HttpResponse(null, { status: 204 });
  }),
];
