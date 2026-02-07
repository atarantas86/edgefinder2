import { useCallback, useEffect, useState } from "react";

const BASE_URL = "http://localhost:8000";

export default function useApi(endpoint, { immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${BASE_URL}${endpoint}`);
      if (!response.ok) {
        throw new Error(`API error ${response.status}`);
      }
      const payload = await response.json();
      setData(payload);
      return payload;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
      return null;
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    if (immediate) {
      fetchData();
    }
  }, [fetchData, immediate]);

  return { data, loading, error, refetch: fetchData };
}
