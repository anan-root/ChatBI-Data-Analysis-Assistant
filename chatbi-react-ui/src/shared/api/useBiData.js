import { useEffect, useState } from 'react';
import { fetchBiData, getBiEndpoint } from './client';

export function useBiData(activeView) {
  const [data, setData] = useState({
    audit: null,
    dashboard: null,
    metrics: null,
    anomalies: null,
    report: null,
    sql: null,
    importClean: null,
    growth: null,
    monetization: null,
    rag: null,
    workspaces: null,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const endpoint = getBiEndpoint(activeView);
    if (!endpoint) return;
    if (data[activeView]) return;

    setLoading(true);
    fetchBiData(activeView)
      .then((json) => setData((current) => ({ ...current, [activeView]: json })))
      .catch((error) => setData((current) => ({ ...current, [activeView]: { error: error.message } })))
      .finally(() => setLoading(false));
  }, [activeView, data]);

  return { data, loading };
}
