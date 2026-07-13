import { describe, expect, it } from 'vitest';
import { snapshotsToCsv } from './csv';
import type { SnapshotDTO } from '../types/api';

function makeSnapshot(overrides: Partial<SnapshotDTO> = {}): SnapshotDTO {
  return {
    id: 1,
    syncedAt: 1700000000,
    moneyOnhand: 100,
    moneyPoints: 0,
    vaultAmount: 0,
    bankAmount: 0,
    energyCurrent: 10,
    energyMaximum: 150,
    nerveCurrent: 5,
    nerveMaximum: 50,
    happyCurrent: 100,
    happyMaximum: 5000,
    networth: 1000,
    nwPending: 0,
    nwWallet: 100,
    nwBank: 0,
    nwPoints: 0,
    nwCayman: 0,
    nwVault: 0,
    nwPiggybank: 0,
    nwItems: 0,
    nwDisplaycase: 0,
    nwBazaar: 0,
    nwItemmarket: 0,
    nwProperties: 0,
    nwStockmarket: 0,
    nwAuctionhouse: 0,
    nwCompany: 0,
    nwBookie: 0,
    nwEnlistedcars: 0,
    nwLoan: 0,
    nwUnpaidfees: 0,
    refillsTotal: 0,
    nerverefillsTotal: 0,
    energydrinkusedTotal: 0,
    xantakenTotal: 0,
    warModeActive: false,
    note: null,
    ...overrides,
  };
}

describe('snapshotsToCsv', () => {
  it('returns an empty string for an empty list', () => {
    expect(snapshotsToCsv([])).toBe('');
  });

  it('writes a header row of every DTO field', () => {
    const csv = snapshotsToCsv([makeSnapshot()]);
    const [header] = csv.split('\n');
    expect(header).toBe(Object.keys(makeSnapshot()).join(','));
  });

  it('writes one data row per snapshot', () => {
    const csv = snapshotsToCsv([makeSnapshot({ id: 1 }), makeSnapshot({ id: 2 })]);
    expect(csv.split('\n')).toHaveLength(3);
  });

  it('renders null as an empty cell', () => {
    const csv = snapshotsToCsv([makeSnapshot({ note: null })]);
    const [, row] = csv.split('\n');
    const noteIndex = Object.keys(makeSnapshot()).indexOf('note');
    expect(row.split(',')[noteIndex]).toBe('');
  });

  it('quotes a value containing a comma', () => {
    const csv = snapshotsToCsv([makeSnapshot({ note: 'War week 1, day 3' })]);
    expect(csv).toContain('"War week 1, day 3"');
  });
});
