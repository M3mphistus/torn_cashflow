import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '../api/client';
import { getMe } from '../api/auth';
import type { PlayerDTO, PremiumStatusDTO } from '../types/api';

export const AUTH_QUERY_KEY = ['auth', 'me'] as const;

export interface AuthState {
  player: PlayerDTO | null;
  premium: PremiumStatusDTO | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isUnauthenticated: boolean;
  error: unknown;
  refetch: () => void;
}

export function useAuth(): AuthState {
  const query = useQuery({ queryKey: AUTH_QUERY_KEY, queryFn: getMe, retry: false });
  const isAuthError = query.error instanceof ApiError && query.error.status === 401;

  return {
    player: query.data?.player ?? null,
    premium: query.data?.premium ?? null,
    isLoading: query.isLoading,
    isAuthenticated: query.isSuccess,
    isUnauthenticated: query.isError && isAuthError,
    error: query.isError && !isAuthError ? query.error : null,
    refetch: () => query.refetch(),
  };
}

export function useInvalidateAuth() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY });
}
