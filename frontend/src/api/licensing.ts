import { apiFetch } from './client';
import type {
  FactionPreviewDTO,
  GroupScanResultDTO,
  LicensingStatusDTO,
  ScanPaymentResultDTO,
  TrialResultDTO,
} from '../types/api';

export function getLicensingStatus(): Promise<LicensingStatusDTO> {
  return apiFetch('/api/licensing/status');
}

export function startTrial(): Promise<TrialResultDTO> {
  return apiFetch('/api/licensing/trial', { method: 'POST' });
}

export function scanPayment(lookbackDays = 7): Promise<ScanPaymentResultDTO> {
  return apiFetch('/api/licensing/scan-payment', {
    method: 'POST',
    body: JSON.stringify({ lookbackDays }),
  });
}

export function getFactionPreview(): Promise<FactionPreviewDTO | null> {
  return apiFetch('/api/licensing/faction-preview');
}

export function scanGroupPayment(lookbackDays = 7): Promise<GroupScanResultDTO> {
  return apiFetch('/api/licensing/scan-group-payment', {
    method: 'POST',
    body: JSON.stringify({ lookbackDays }),
  });
}
