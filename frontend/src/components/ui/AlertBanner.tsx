import type { ReactNode } from 'react';

type Kind = 'info' | 'success' | 'warning' | 'error';

export default function AlertBanner({ kind = 'info', children }: { kind?: Kind; children: ReactNode }) {
  return <div className={`alert-banner ${kind}`}>{children}</div>;
}
