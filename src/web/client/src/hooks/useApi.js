import { useState, useEffect, useCallback } from 'react';

export function useApi(apiFn, ...args) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiFn(...args);
      setData(result);
    } catch (err) {
      console.error('API error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiFn, ...args]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const refetch = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch };
}
