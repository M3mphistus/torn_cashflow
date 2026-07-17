import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth, useInvalidateAuth } from '../hooks/useAuth';
import { login, logout } from '../api/auth';
import { getWarMode, setWarMode } from '../api/settings';
import { getLicensingStatus, startTrial, scanPayment, getFactionPreview, scanGroupPayment } from '../api/licensing';
import { getLifetimeGrants, createLifetimeGrant, deleteLifetimeGrant } from '../api/admin';
import { clearAllData } from '../api/data';
import { ApiError } from '../api/client';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { formatTimestamp, formatDays } from '../lib/format';
import { API_KEY_CREATE_URL, DEV_PROFILE_URL, DEV_PROFILE_LABEL, GITHUB_REPO_URL } from '../constants';
import type { GrantScope } from '../types/api';

const SOURCE_LABELS: Record<string, string> = {
  trial: 'your free trial',
  individual: 'your payment',
  faction: 'your faction',
  lifetimeIndividual: 'a lifetime grant',
  lifetimeFaction: "your faction's lifetime grant",
};

export default function SettingsPage() {
  const { player, premium } = useAuth();
  const invalidateAuth = useInvalidateAuth();
  const queryClient = useQueryClient();

  const [apiKeyInput, setApiKeyInput] = useState('');
  const reKeyMutation = useMutation({
    mutationFn: () => login(apiKeyInput.trim()),
    onSuccess: () => {
      invalidateAuth();
      setApiKeyInput('');
    },
  });
  const logoutMutation = useMutation({ mutationFn: logout, onSuccess: () => invalidateAuth() });

  const warModeQuery = useQuery({ queryKey: ['warMode'], queryFn: getWarMode });
  const warModeMutation = useMutation({
    mutationFn: setWarMode,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['warMode'] }),
  });

  const licensingQuery = useQuery({ queryKey: ['licensing', 'status'], queryFn: getLicensingStatus });
  const trialMutation = useMutation({
    mutationFn: startTrial,
    onSuccess: () => {
      invalidateAuth();
      queryClient.invalidateQueries({ queryKey: ['licensing'] });
    },
  });

  const [payMode, setPayMode] = useState<'individual' | 'faction'>('individual');
  const factionPreviewQuery = useQuery({
    queryKey: ['licensing', 'factionPreview'],
    queryFn: getFactionPreview,
    enabled: payMode === 'faction' && !!player?.factionId,
  });
  const scanPaymentMutation = useMutation({
    mutationFn: () => scanPayment(),
    onSuccess: () => {
      invalidateAuth();
      queryClient.invalidateQueries({ queryKey: ['licensing'] });
    },
  });
  const scanGroupPaymentMutation = useMutation({
    mutationFn: () => scanGroupPayment(),
    onSuccess: () => {
      invalidateAuth();
      queryClient.invalidateQueries({ queryKey: ['licensing'] });
    },
  });

  const grantsQuery = useQuery({ queryKey: ['admin', 'grants'], queryFn: getLifetimeGrants, enabled: !!player?.isAdmin });
  const [grantScope, setGrantScope] = useState<GrantScope>('individual');
  const [grantKey, setGrantKey] = useState('');
  const createGrantMutation = useMutation({
    mutationFn: () => createLifetimeGrant(grantScope, Number(grantKey)),
    onSuccess: () => {
      setGrantKey('');
      queryClient.invalidateQueries({ queryKey: ['admin', 'grants'] });
    },
  });
  const revokeGrantMutation = useMutation({
    mutationFn: ({ scope, key }: { scope: GrantScope; key: number }) => deleteLifetimeGrant(scope, key),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'grants'] }),
  });

  const [confirmClear, setConfirmClear] = useState(false);
  const clearMutation = useMutation({
    mutationFn: clearAllData,
    onSuccess: () => {
      setConfirmClear(false);
      queryClient.invalidateQueries();
    },
  });

  if (!player || !premium) return null;

  return (
    <div className="page">
      <h1>Settings</h1>

      <SectionHeading>Torn API Key</SectionHeading>
      <p>
        <a href={API_KEY_CREATE_URL} target="_blank" rel="noreferrer">
          Click here to create a scoped API key
        </a>{' '}
        — this opens Torn's own key creation page with exactly the permissions this app needs
        pre-checked, nothing more. No blanket Full Access required.
      </p>
      <details>
        <summary>What does this app access, and why?</summary>
        <ul>
          <li>
            <strong>Basic profile</strong> — your name and faction, so your data is scoped to your account.
          </li>
          <li>
            <strong>Bars</strong> — energy/nerve/happy, for the Dashboard KPIs.
          </li>
          <li>
            <strong>Money</strong> — cash on hand, vault, and bank, for cashflow tracking.
          </li>
          <li>
            <strong>Personal stats</strong> — net worth and its breakdown.
          </li>
          <li>
            <strong>Log</strong> — your activity log, used to build categorized cashflow history and to detect Xanax payments for Premium.
          </li>
        </ul>
        <p>
          That's the complete list — nothing is ever written back to Torn through this key, it's
          used read-only. The key itself is remembered only via your browser's session cookie,
          never written to a shared file, and never logged.
        </p>
      </details>

      <p>
        Signed in as <strong>{player.name}</strong> (player id {player.playerId}), key <code>{player.maskedApiKey}</code>.
      </p>

      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            reKeyMutation.mutate();
          }}
        >
          <label htmlFor="settings-api-key">Torn API key</label>
          <input id="settings-api-key" type="password" value={apiKeyInput} onChange={(e) => setApiKeyInput(e.target.value)} autoComplete="off" />
          <div style={{ marginTop: 8 }}>
            <Button type="submit" disabled={!apiKeyInput.trim() || reKeyMutation.isPending}>
              Save key
            </Button>
          </div>
        </form>
      </Card>
      {reKeyMutation.isSuccess && (
        <AlertBanner kind="success">
          Signed in as {reKeyMutation.data.player.name} (player id {reKeyMutation.data.player.playerId}).
        </AlertBanner>
      )}
      {reKeyMutation.isError && (
        <AlertBanner kind="error">{reKeyMutation.error instanceof ApiError ? reKeyMutation.error.message : 'Something went wrong.'}</AlertBanner>
      )}

      <div style={{ marginTop: 8 }}>
        <Button onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}>
          Log out
        </Button>
      </div>

      <hr />
      <SectionHeading>Privacy, Data &amp; Source</SectionHeading>
      <p>
        This app is fully open source —{' '}
        <a href={GITHUB_REPO_URL} target="_blank" rel="noreferrer">
          read the code on GitHub
        </a>
        .
      </p>
      <details>
        <summary>What's stored, and how to remove it</summary>
        <ul>
          <li>
            <strong>Your Torn player ID, name, and faction</strong> — used to scope every query to your account only.
          </li>
          <li>
            <strong>Synced snapshots and log entries</strong> — whatever you've pulled in via Sync, stored in a shared Postgres database, isolated
            per Torn player ID. No other player can see your data.
          </li>
          <li>
            <strong>Checklist tasks and category rules</strong> — your own personal setup.
          </li>
          <li>
            <strong>Premium/license status</strong> — whether you're on a trial, paid, or lifetime grant.
          </li>
        </ul>
        <p>
          To remove your synced data, use <strong>Clear DB</strong> in the Danger Zone below — it
          permanently deletes your snapshots, log entries, and category rules. It does not
          currently remove your player record or Premium/license history; if you'd like your
          account fully deleted, contact the developer directly.
        </p>
        <p>
          This is an independent hobby project, not affiliated with or endorsed by Torn. It's
          provided as-is, with no warranty — use your own judgment, same as with any third-party
          tool that reads your Torn API data.
        </p>
      </details>

      <hr />
      <SectionHeading>Feedback &amp; Suggestions</SectionHeading>
      <p>
        Found a bug, or have an idea for a feature? Send a Torn message to{' '}
        <a href={DEV_PROFILE_URL} target="_blank" rel="noreferrer">
          {DEV_PROFILE_LABEL}
        </a>{' '}
        — all feedback and suggestions are welcome.
      </p>

      <hr />
      <SectionHeading>War Mode</SectionHeading>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, textTransform: 'none' }}>
        <input
          type="checkbox"
          style={{ width: 'auto' }}
          checked={warModeQuery.data?.active ?? false}
          onChange={(e) => warModeMutation.mutate(e.target.checked)}
        />
        War Mode active
      </label>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Turn this on during a ranked war. It drives auto-categorization of log entries as 'Ranked
        War' during sync, and controls which 'On War Days' checklist tasks are shown/reset.
      </p>

      <hr />
      <SectionHeading>Premium / License</SectionHeading>
      {premium.isPremium ? (
        premium.isLifetime ? (
          <AlertBanner kind="success">Premium active via {SOURCE_LABELS[premium.source] ?? premium.source} — forever.</AlertBanner>
        ) : (
          <AlertBanner kind={premium.isExpiringSoon ? 'warning' : 'success'}>
            Premium active via {SOURCE_LABELS[premium.source] ?? premium.source}
            {premium.premiumUntil && `, until ${formatTimestamp(premium.premiumUntil)}`}.
            {premium.isExpiringSoon && premium.daysUntilExpiry !== null && (
              <>
                {' '}
                Expires in <strong>{formatDays(premium.daysUntilExpiry)} day(s)</strong> — extend it below before it runs out.
              </>
            )}
          </AlertBanner>
        )
      ) : (
        <AlertBanner kind="info">Free tier.</AlertBanner>
      )}

      <p>
        Send <strong>1 Xanax</strong> to{' '}
        <a href={DEV_PROFILE_URL} target="_blank" rel="noreferrer">
          {DEV_PROFILE_LABEL}
        </a>{' '}
        for 4 weeks of Premium.
      </p>

      {!licensingQuery.data?.trialUsed && !premium.isPremium && (
        <Button onClick={() => trialMutation.mutate()} disabled={trialMutation.isPending}>
          Start my 7-day free trial
        </Button>
      )}
      {trialMutation.data && (
        <AlertBanner kind={trialMutation.data.started ? 'success' : 'error'}>
          {trialMutation.data.started
            ? `Trial started! Premium until ${formatTimestamp(trialMutation.data.premiumUntil!)}.`
            : trialMutation.data.reason}
        </AlertBanner>
      )}

      <h4 style={{ marginTop: 20 }}>Pay for Premium</h4>
      <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, textTransform: 'none' }}>
          <input type="radio" style={{ width: 'auto' }} checked={payMode === 'individual'} onChange={() => setPayMode('individual')} />
          Just myself
        </label>
        {player.factionId && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, textTransform: 'none' }}>
            <input type="radio" style={{ width: 'auto' }} checked={payMode === 'faction'} onChange={() => setPayMode('faction')} />
            My whole faction (bulk)
          </label>
        )}
      </div>

      {payMode === 'faction' ? (
        factionPreviewQuery.data ? (
          <p>
            Your faction has <strong>{factionPreviewQuery.data.memberCount}</strong> members (
            {factionPreviewQuery.data.discountPct > 0 ? `${(factionPreviewQuery.data.discountPct * 100).toFixed(0)}%` : 'no'} bulk discount) — send{' '}
            <strong>{factionPreviewQuery.data.required} Xanax</strong> total to cover everyone for 4 weeks
            {factionPreviewQuery.data.lifetimeCoveredCount > 0 &&
              ` (${factionPreviewQuery.data.lifetimeCoveredCount} member(s) already have lifetime Premium and aren't counted)`}
            .
          </p>
        ) : (
          <AlertBanner kind="warning">Could not read your faction's member list right now — try again shortly.</AlertBanner>
        )
      ) : (
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>1 Xanax covers 4 weeks of Premium for your account only.</p>
      )}

      <Button
        onClick={() => (payMode === 'faction' ? scanGroupPaymentMutation.mutate() : scanPaymentMutation.mutate())}
        disabled={scanPaymentMutation.isPending || scanGroupPaymentMutation.isPending}
      >
        Check my payment now
      </Button>

      {scanPaymentMutation.data && (
        <AlertBanner kind="info">
          {scanPaymentMutation.data.creditedCount > 0
            ? `Credited ${scanPaymentMutation.data.weeksAdded} week(s) from ${scanPaymentMutation.data.creditedCount} payment(s).`
            : 'No new qualifying payment found in the last 7 days.'}
        </AlertBanner>
      )}
      {scanGroupPaymentMutation.data && <AlertBanner kind="info">{scanGroupPaymentMutation.data.message}</AlertBanner>}

      {player.isAdmin && (
        <>
          <hr />
          <SectionHeading>Admin: Lifetime Premium Grants</SectionHeading>
          <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Only visible to the developer account.</p>

          <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, textTransform: 'none' }}>
              <input type="radio" style={{ width: 'auto' }} checked={grantScope === 'individual'} onChange={() => setGrantScope('individual')} />
              Individual player
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, textTransform: 'none' }}>
              <input type="radio" style={{ width: 'auto' }} checked={grantScope === 'faction'} onChange={() => setGrantScope('faction')} />
              Faction
            </label>
          </div>
          <label htmlFor="grant-id">{grantScope === 'individual' ? 'Torn player ID' : 'Faction ID'}</label>
          <input id="grant-id" type="number" min={1} value={grantKey} onChange={(e) => setGrantKey(e.target.value)} style={{ maxWidth: 200 }} />
          <div style={{ marginTop: 8 }}>
            <Button onClick={() => createGrantMutation.mutate()} disabled={!grantKey || createGrantMutation.isPending}>
              Grant lifetime Premium
            </Button>
          </div>

          {grantsQuery.data && grantsQuery.data.grants.length > 0 ? (
            <div style={{ marginTop: 12 }}>
              <p>Current lifetime grants:</p>
              {grantsQuery.data.grants.map((grant) => (
                <div key={`${grant.scope}-${grant.key}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                  <span>
                    <strong>{grant.scope}</strong> — {grant.key}
                  </span>
                  <Button onClick={() => revokeGrantMutation.mutate({ scope: grant.scope, key: grant.key })}>Revoke</Button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>No lifetime grants yet.</p>
          )}
        </>
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
