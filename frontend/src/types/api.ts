export interface PlayerDTO {
  playerId: number;
  name: string | null;
  factionId: number | null;
  maskedApiKey: string;
  isAdmin: boolean;
}

export type PremiumSource = 'none' | 'trial' | 'individual' | 'faction' | 'lifetimeIndividual' | 'lifetimeFaction';

export interface PremiumStatusDTO {
  isPremium: boolean;
  premiumUntil: number | null;
  isLifetime: boolean;
  source: PremiumSource;
  isExpiringSoon: boolean;
  daysUntilExpiry: number | null;
}

export interface SessionDTO {
  player: PlayerDTO;
  premium: PremiumStatusDTO;
}

export interface SnapshotDTO {
  id: number;
  syncedAt: number;
  moneyOnhand: number;
  moneyPoints: number;
  vaultAmount: number;
  bankAmount: number;
  energyCurrent: number;
  energyMaximum: number;
  nerveCurrent: number;
  nerveMaximum: number;
  happyCurrent: number;
  happyMaximum: number;
  networth: number;
  nwPending: number;
  nwWallet: number;
  nwBank: number;
  nwPoints: number;
  nwCayman: number;
  nwVault: number;
  nwPiggybank: number;
  nwItems: number;
  nwDisplaycase: number;
  nwBazaar: number;
  nwItemmarket: number;
  nwProperties: number;
  nwStockmarket: number;
  nwAuctionhouse: number;
  nwCompany: number;
  nwBookie: number;
  nwEnlistedcars: number;
  nwLoan: number;
  nwUnpaidfees: number;
  refillsTotal: number;
  nerverefillsTotal: number;
  energydrinkusedTotal: number;
  xantakenTotal: number;
  warModeActive: boolean;
  note: string | null;
}

export interface CategoryBreakdownRow {
  category: string;
  amount: number;
}

export interface NetworthBreakdownRow {
  component: string;
  amount: number | null;
}

export interface DailyCashflowRow {
  date: string;
  cashflowDelta: number;
}

export interface DailyNetworthRow {
  date: string;
  networth: number;
}

export interface DashboardDTO {
  cashflowTotal: number;
  cashflowPerDay: number;
  categoryBreakdown: CategoryBreakdownRow[];
  networthBreakdown: NetworthBreakdownRow[];
  dailyCashflow: DailyCashflowRow[];
  dailyNetworth: DailyNetworthRow[];
  snapshots: SnapshotDTO[];
}

export interface DashboardBoundsDTO {
  minTs: number | null;
  maxTs: number | null;
}

export interface LogEntryDTO {
  id: number;
  tornLogId: string;
  timestamp: number;
  category: string;
  title: string;
  rawText: string;
  amount: number | null;
  appCategory: string;
  userNote: string | null;
}

export interface CategoryDTO {
  name: string;
  entryCount: number;
}

export interface TitleSummaryRow {
  title: string;
  category: string;
  entryCount: number;
  exampleAmount: number | null;
  amountSign: 1 | -1 | null;
}

export type RepeatType = 'daily' | 'weekly' | 'every_x_days' | 'once' | 'war_day';

export interface ChecklistTaskDTO {
  id: number;
  title: string;
  description: string | null;
  repeatType: RepeatType;
  repeatIntervalDays: number | null;
  createdAt: number;
  lastCompletedAt: number | null;
  isDoneCurrentCycle: boolean;
}

export interface WarModeDTO {
  active: boolean;
  startedAt: number | null;
}

export interface LicensingStatusDTO extends PremiumStatusDTO {
  trialUsed: boolean;
}

export interface TrialResultDTO {
  started: boolean;
  reason: string | null;
  premiumUntil: number | null;
}

export interface ScanPaymentResultDTO {
  creditedCount: number;
  weeksAdded: number;
  newPremiumUntil: number | null;
  alreadyCreditedCount: number;
}

export interface FactionPreviewDTO {
  memberCount: number;
  lifetimeCoveredCount: number;
  payableMembers: number;
  discountPct: number;
  required: number;
}

export interface GroupScanResultDTO {
  activated: boolean;
  message: string;
  required: number | null;
  sent: number | null;
}

export type GrantScope = 'individual' | 'faction';

export interface LifetimeGrantDTO {
  scope: GrantScope;
  key: number;
  activatedAt: number;
}

export interface SyncIncrementalResultDTO {
  snapshot: SnapshotDTO;
  logEntriesStored: number;
  paymentMessage: string | null;
}

export interface FullHistoryJobStartDTO {
  jobId: number;
  status: 'running';
}

export type FullHistoryJobStatus = 'running' | 'completed' | 'failed';

export interface FullHistoryJobDTO {
  jobId: number;
  status: FullHistoryJobStatus;
  pagesFetched: number;
  entriesFetched: number;
  oldestTimestamp: number | null;
  error: string | null;
  result: { newEntriesStored: number; alreadyStored: number } | null;
}

export interface ApiErrorBody {
  message: string;
  code: string;
  tornErrorCode: number | null;
}
