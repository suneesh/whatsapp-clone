import { API_BASE_URL } from '../config';

/**
 * Wrapper around fetch that automatically prepends API_BASE_URL
 */
export async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  const url = path.startsWith('/') ? `${API_BASE_URL}${path}` : `${API_BASE_URL}/${path}`;
  return fetch(url, options);
}
