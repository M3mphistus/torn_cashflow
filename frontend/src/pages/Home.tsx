import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { getLatestSnapshot } from '../api/snapshots';
import AlertBanner from '../components/ui/AlertBanner';
import NavCard from '../components/layout/NavCard';
import { formatTimestamp, formatDays } from '../lib/format';
import { GITHUB_REPO_URL, DEV_PROFILE_URL, DEV_PROFILE_LABEL } from '../constants';

export default function HomePage() {
  const { player, premium } = useAuth();
  const { data } = useQuery({ queryKey: ['snapshots', 'latest'], queryFn: getLatestSnapshot });
  const latest = data?.snapshot ?? null;

  return (
    <div className="page">
      <p className="eyebrow">A SPEAKEASY LEDGER FOR TORN CITY</p>
      <h1>Torn Cashflow Dashboard</h1>
      <p>
        Track your cashflow, energy/nerve spend, networth, and a recurring checklist — all pulled
        straight from your own Torn account. Create a scoped API key once in Settings and you'll
        stay signed in on this browser.
      </p>

      {player && (
        <AlertBanner kind="success">
          Signed in as <strong>{player.name}</strong> (player id {player.playerId})
          {player.factionId ? ` — faction ${player.factionId}` : ''}.
        </AlertBanner>
      )}

      {premium?.isExpiringSoon && premium.daysUntilExpiry !== null && (
        <AlertBanner kind="warning">
          Your Premium expires in <strong>{formatDays(premium.daysUntilExpiry)} day(s)</strong> —
          extend it on the <Link to="/settings">Settings</Link> page before it runs out.
        </AlertBanner>
      )}

      {latest ? (
        <p>Last synced at: {formatTimestamp(latest.syncedAt)}</p>
      ) : (
        <AlertBanner kind="info">
          No sync data yet. <Link to="/sync">Go to Sync</Link> to pull your first snapshot.
        </AlertBanner>
      )}

      <hr />

      <div className="nav-grid">
        <NavCard to="/dashboard" title="Dashboard" caption="KPIs, cashflow-by-category, networth breakdown, and the raw snapshot table." />
        <NavCard to="/sync" title="Sync" caption="Pull fresh data from the Torn API and review auto-categorized log entries." />
        <NavCard to="/checklist" title="Checklist" caption="Recurring and one-off tasks — daily refills, war prep, and more." />
        <NavCard
          to="/categories"
          title="Categories"
          premium={!premium?.isPremium}
          caption="Manage categories and bulk-recategorize log entries by title."
        />
        <NavCard to="/settings" title="Settings" caption="API key, War Mode toggle, and your Premium/License status." />
      </div>

      <footer className="page-footer">
        <p>
          Free tier covers day-to-day tracking. Premium (full history sync, Categories, and
          automatic checklist resets) unlocks with a 7-day free trial or by sending Xanax in-game —
          see Settings.
        </p>
        <p>
          This app is fully open source —{' '}
          <a href={GITHUB_REPO_URL} target="_blank" rel="noreferrer">
            read the code on GitHub
          </a>
          . Not affiliated with or endorsed by Torn. See Settings for what data is accessed/stored
          and how to remove it.
        </p>
        <p>
          Feedback or suggestions? Send a Torn message to{' '}
          <a href={DEV_PROFILE_URL} target="_blank" rel="noreferrer">
            {DEV_PROFILE_LABEL}
          </a>{' '}
          — see Settings.
        </p>
      </footer>
    </div>
  );
}
