import type {
  ChecklistTaskDTO,
  LifetimeGrantDTO,
  LogEntryDTO,
  PlayerDTO,
  PremiumStatusDTO,
  SnapshotDTO,
  WarModeDTO,
} from '../types/api';

export const mockSession = { loggedIn: false, trialUsed: false };

export const mockPlayer: PlayerDTO = {
  playerId: 4316364,
  name: 'MockPlayer',
  factionId: 7890,
  maskedApiKey: '****mock',
  isAdmin: true,
};

export const mockPremium: PremiumStatusDTO = {
  isPremium: true,
  premiumUntil: Math.floor(Date.now() / 1000) + 10 * 86400,
  isLifetime: false,
  source: 'individual',
  isExpiringSoon: false,
  daysUntilExpiry: 10,
};

export function makeSnapshot(daysAgo: number, overrides: Partial<SnapshotDTO> = {}): SnapshotDTO {
  const syncedAt = Math.floor(Date.now() / 1000) - daysAgo * 86400;
  return {
    id: 1000 - daysAgo,
    syncedAt,
    moneyOnhand: 500000 + daysAgo * 1000,
    moneyPoints: 12000,
    vaultAmount: 2000000,
    bankAmount: 100000,
    energyCurrent: 90,
    energyMaximum: 150,
    nerveCurrent: 20,
    nerveMaximum: 50,
    happyCurrent: 4000,
    happyMaximum: 5000,
    networth: 15000000 - daysAgo * 20000,
    nwPending: 0,
    nwWallet: 500000,
    nwBank: 100000,
    nwPoints: 1200000,
    nwCayman: 0,
    nwVault: 2000000,
    nwPiggybank: 0,
    nwItems: 3000000,
    nwDisplaycase: 0,
    nwBazaar: 0,
    nwItemmarket: 0,
    nwProperties: 5000000,
    nwStockmarket: 0,
    nwAuctionhouse: 0,
    nwCompany: 0,
    nwBookie: 0,
    nwEnlistedcars: 0,
    nwLoan: 0,
    nwUnpaidfees: 0,
    refillsTotal: 40,
    nerverefillsTotal: 5,
    energydrinkusedTotal: 12,
    xantakenTotal: 8,
    warModeActive: false,
    note: daysAgo === 0 ? 'Latest sync' : null,
    ...overrides,
  };
}

export const mockSnapshots: SnapshotDTO[] = Array.from({ length: 14 }, (_, i) => makeSnapshot(13 - i));

export const mockLogEntries: LogEntryDTO[] = [
  {
    id: 1,
    tornLogId: '111',
    timestamp: Math.floor(Date.now() / 1000) - 2 * 86400,
    category: 'Attacking',
    title: 'Attacked player X',
    rawText: 'You attacked player X and won, gaining $50,000',
    amount: 50000,
    appCategory: 'Ranked War',
    userNote: null,
  },
  {
    id: 2,
    tornLogId: '112',
    timestamp: Math.floor(Date.now() / 1000) - 1 * 86400,
    category: 'Item sending',
    title: 'Item send',
    rawText: 'You sent 4x Xanax to SomePlayer',
    amount: null,
    appCategory: 'Uncategorized',
    userNote: null,
  },
  {
    id: 3,
    tornLogId: '113',
    timestamp: Math.floor(Date.now() / 1000) - 3 * 3600,
    category: 'Job',
    title: 'Received company pay',
    rawText: 'You worked a shift and earned $12,000',
    amount: 12000,
    appCategory: 'Job',
    userNote: null,
  },
  {
    id: 4,
    tornLogId: '114',
    timestamp: Math.floor(Date.now() / 1000) - 5 * 3600,
    category: 'Mystery',
    title: 'Unusual event',
    rawText: 'Something happened that nothing recognizes',
    amount: -3000,
    appCategory: 'Uncategorized',
    userNote: null,
  },
];

export const mockCategories: string[] = ['Ranked War', 'Flying', 'Job', 'Gift', 'Casino'];

export const mockChecklistTasks: ChecklistTaskDTO[] = [
  {
    id: 1,
    title: 'Use energy refill',
    description: 'Spend the daily energy refill before it resets.',
    repeatType: 'daily',
    repeatIntervalDays: null,
    createdAt: Math.floor(Date.now() / 1000) - 30 * 86400,
    lastCompletedAt: null,
    isDoneCurrentCycle: false,
  },
  {
    id: 2,
    title: 'Check faction OCs',
    description: null,
    repeatType: 'every_x_days',
    repeatIntervalDays: 2,
    createdAt: Math.floor(Date.now() / 1000) - 20 * 86400,
    lastCompletedAt: null,
    isDoneCurrentCycle: false,
  },
  {
    id: 3,
    title: 'Rotate war targets',
    description: 'Only shown while War Mode is active.',
    repeatType: 'war_day',
    repeatIntervalDays: null,
    createdAt: Math.floor(Date.now() / 1000) - 5 * 86400,
    lastCompletedAt: null,
    isDoneCurrentCycle: false,
  },
];

export const mockWarMode: WarModeDTO = { active: false, startedAt: null };

export const mockLifetimeGrants: LifetimeGrantDTO[] = [
  { scope: 'individual', key: 1234567, activatedAt: Math.floor(Date.now() / 1000) - 100 * 86400 },
];
