import type { ReactNode } from 'react';
import PremiumBadge from './PremiumBadge';

export default function SectionHeading({ children, premium = false }: { children: ReactNode; premium?: boolean }) {
  return (
    <h3>
      {children}
      {premium && <PremiumBadge />}
    </h3>
  );
}
