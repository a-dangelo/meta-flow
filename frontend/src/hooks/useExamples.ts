/**
 * useExamples Hook
 * Manages loading and caching of workflow examples
 */

import { useState, useEffect, useCallback } from 'react';
import { getExamples } from '@/services/api';
import { useLocalStorage } from './useLocalStorage';
import type { ExampleSpec, ExamplesResponse } from '@/types';

interface UseExamplesReturn {
  examples: ExampleSpec[];
  loading: boolean;
  error: string | null;
  selectedExample: ExampleSpec | null;
  selectExample: (example: ExampleSpec | null) => void;
  refreshExamples: () => Promise<void>;
  getExampleByName: (name: string) => ExampleSpec | undefined;
}

/**
 * Custom hook for managing workflow examples
 */
export function useExamples(): UseExamplesReturn {
  const [examples, setExamples] = useState<ExampleSpec[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedExample, setSelectedExample] = useState<ExampleSpec | null>(null);

  // Cache examples in localStorage (1 hour cache)
  const [cachedExamples, setCachedExamples] = useLocalStorage<{
    data: ExamplesResponse | null;
    timestamp: number;
  }>('meta-flow-examples-cache', { data: null, timestamp: 0 });

  /**
   * Load examples from API or cache
   */
  const loadExamples = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    setError(null);

    try {
      const now = Date.now();
      const ONE_HOUR = 60 * 60 * 1000;

      // Check if we have valid cached data
      if (
        !forceRefresh &&
        cachedExamples.data &&
        now - cachedExamples.timestamp < ONE_HOUR
      ) {
        setExamples(cachedExamples.data.examples);
        setLoading(false);
        return;
      }

      // Fetch fresh data from API
      const response = await getExamples();
      setExamples(response.examples);

      // Update cache
      setCachedExamples({
        data: response,
        timestamp: now,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load examples';
      setError(errorMessage);
      console.error('Error loading examples:', err);

      // Fall back to cached data if available
      if (cachedExamples.data) {
        setExamples(cachedExamples.data.examples);
        setError(errorMessage + ' (using cached data)');
      }
    } finally {
      setLoading(false);
    }
  }, [cachedExamples, setCachedExamples]);

  /**
   * Refresh examples (force reload from API)
   */
  const refreshExamples = useCallback(async () => {
    await loadExamples(true);
  }, [loadExamples]);

  /**
   * Get example by name
   */
  const getExampleByName = useCallback(
    (name: string): ExampleSpec | undefined => {
      return examples.find((ex) => ex.name === name);
    },
    [examples]
  );

  /**
   * Select an example
   */
  const selectExample = useCallback((example: ExampleSpec | null) => {
    setSelectedExample(example);
  }, []);

  // Load examples on mount
  useEffect(() => {
    loadExamples();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    examples,
    loading,
    error,
    selectedExample,
    selectExample,
    refreshExamples,
    getExampleByName,
  };
}

export default useExamples;