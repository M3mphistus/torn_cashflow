import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { login } from '../api/auth';
import { ApiError } from '../api/client';
import { useInvalidateAuth } from '../hooks/useAuth';
import Card from '../components/ui/Card';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import { API_KEY_CREATE_URL } from '../constants';

export default function LoginPage() {
  const [apiKey, setApiKey] = useState('');
  const invalidateAuth = useInvalidateAuth();
  const mutation = useMutation({
    mutationFn: () => login(apiKey.trim()),
    onSuccess: () => invalidateAuth(),
  });

  return (
    <div className="page" style={{ maxWidth: 520 }}>
      <p className="eyebrow">A SPEAKEASY LEDGER FOR TORN CITY</p>
      <h1>Torn Cashflow Dashboard</h1>
      <p>
        Paste a Torn API key to sign in. Use a scoped, read-only key —{' '}
        <a href={API_KEY_CREATE_URL} target="_blank" rel="noreferrer">
          click here to create one
        </a>{' '}
        with exactly the permissions this app needs pre-checked. No blanket Full Access required.
      </p>

      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
        >
          <label htmlFor="api-key">Torn API key</label>
          <input id="api-key" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} autoComplete="off" />
          <div style={{ marginTop: 12 }}>
            <Button type="submit" variant="primary" disabled={mutation.isPending || !apiKey.trim()}>
              {mutation.isPending ? 'Signing in…' : 'Sign in'}
            </Button>
          </div>
        </form>
      </Card>

      {mutation.isError && (
        <AlertBanner kind="error">{mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}</AlertBanner>
      )}
    </div>
  );
}
