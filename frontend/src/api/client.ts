import type { ApiErrorBody } from '../types/api';

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '';

export class ApiError extends Error {
  status: number;
  code: string;
  tornErrorCode: number | null;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code;
    this.tornErrorCode = body.tornErrorCode ?? null;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const errorBody: ApiErrorBody = data?.error ?? {
      message: 'Something went wrong talking to the server.',
      code: 'unknown_error',
      tornErrorCode: null,
    };
    throw new ApiError(response.status, errorBody);
  }

  return data as T;
}
