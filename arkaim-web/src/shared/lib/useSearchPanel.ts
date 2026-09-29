'use client';

import { useState, useCallback } from 'react';
import { api } from '@/shared/lib/api';

type UseSearchPanelOptions<T> = {
  apiPath: string;
  transform?: (data: Record<string, unknown>) => T[];
  requestBody?: Record<string, unknown>;
};

export function useSearchPanel<T = Record<string, unknown>>(opts: UseSearchPanelOptions<T>) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const search = useCallback(async (q?: string) => {
    const searchTerm = q ?? query;
    if (!searchTerm.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const body = { query: searchTerm.trim(), ...opts.requestBody };
      const data = await api.post<any>(opts.apiPath, body);
      setResults(opts.transform ? opts.transform(data) : data.results || data.facts || data.entities || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query, opts.apiPath, opts.transform, opts.requestBody]);

  const reset = useCallback(() => {
    setQuery('');
    setResults([]);
    setSearched(false);
  }, []);

  return { query, setQuery, results, loading, searched, search, reset };
}
