import { useCallback, useEffect, useRef, useState } from "react";

export interface Polled<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

/** Poll a read-only endpoint. Keeps the last good value on transient errors. */
export function usePoll<T>(fetcher: () => Promise<T>, intervalMs: number): Polled<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const ref = useRef(fetcher);
  ref.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      setData(await ref.current());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const t = window.setInterval(refresh, intervalMs);
    return () => window.clearInterval(t);
  }, [refresh, intervalMs]);

  return { data, error, loading, refresh };
}
