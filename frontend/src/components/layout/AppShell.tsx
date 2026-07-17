import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { logout } from '../../api/auth';
import { useInvalidateAuth } from '../../hooks/useAuth';
import PremiumBadge from '../ui/PremiumBadge';
import Button from '../ui/Button';
import type { PlayerDTO, PremiumStatusDTO } from '../../types/api';

const NAV_ITEMS = [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/checklist', label: 'Checklist' },
  { to: '/categories', label: 'Categories' },
  { to: '/settings', label: 'Settings' },
];

export default function AppShell({
  player,
  premium,
  children,
}: {
  player: PlayerDTO;
  premium: PremiumStatusDTO;
  children: ReactNode;
}) {
  const invalidateAuth = useInvalidateAuth();
  const logoutMutation = useMutation({ mutationFn: logout, onSuccess: () => invalidateAuth() });

  return (
    <div>
      <div className="app-shell-top">
        <nav className="app-shell-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
              {item.label}
              {item.to === '/categories' && !premium.isPremium && <PremiumBadge />}
            </NavLink>
          ))}
        </nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="eyebrow">
            {player.name} {premium.isPremium && <PremiumBadge />}
          </span>
          <Button onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}>
            Log out
          </Button>
        </div>
      </div>
      {children}
    </div>
  );
}
