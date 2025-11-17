/**
 * useGenerate Hook
 * Manages the agent generation workflow with progress tracking
 */

import { useState, useCallback, useRef } from 'react';
import { generateAgent, cancelRequest, APIServiceError } from '@/services/api';
import { useLocalStorage } from './useLocalStorage';
import type { GenerateRequest, GenerateResponse, PipelineStage } from '@/types';

interface GenerationHistory {
  id: string;
  request: GenerateRequest;
  response: GenerateResponse | null;
  error: string | null;
  timestamp: number;
}

interface UseGenerateReturn {
  // State
  isGenerating: boolean;
  currentStage: PipelineStage;
  progress: number;
  error: string | null;
  lastResult: GenerateResponse | null;

  // History
  history: GenerationHistory[];
  clearHistory: () => void;

  // Actions
  generate: (request: GenerateRequest) => Promise<GenerateResponse | null>;
  cancel: () => void;
  reset: () => void;
}

/**
 * Map API progress stages to pipeline stages
 */
const mapApiStageToPipelineStage = (stage: string): PipelineStage => {
  const stageMap: Record<string, PipelineStage> = {
    parsing: 'parsing',
    validating: 'validating',
    generating: 'generating_json',
    generating_json: 'generating_json',
    generating_code: 'generating_code',
    complete: 'complete',
    error: 'error',
  };
  return stageMap[stage.toLowerCase()] || 'idle';
};

/**
 * Custom hook for managing agent generation
 */
export function useGenerate(): UseGenerateReturn {
  // State
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStage, setCurrentStage] = useState<PipelineStage>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<GenerateResponse | null>(null);

  // History management
  const [history, setHistory, clearHistory] = useLocalStorage<GenerationHistory[]>(
    'meta-flow-generation-history',
    []
  );

  // Ref to track if generation was cancelled
  const isCancelledRef = useRef(false);

  /**
   * Progress callback for API calls
   */
  const handleProgress = useCallback((stage: string, progressValue: number) => {
    if (isCancelledRef.current) return;

    const pipelineStage = mapApiStageToPipelineStage(stage);
    setCurrentStage(pipelineStage);

    // Calculate overall progress based on stage
    let overallProgress = progressValue;
    switch (pipelineStage) {
      case 'parsing':
        overallProgress = Math.min(progressValue * 0.2, 20); // 0-20%
        break;
      case 'validating':
        overallProgress = 20 + Math.min(progressValue * 0.1, 10); // 20-30%
        break;
      case 'generating_json':
        overallProgress = 30 + Math.min(progressValue * 0.3, 30); // 30-60%
        break;
      case 'generating_code':
        overallProgress = 60 + Math.min(progressValue * 0.35, 35); // 60-95%
        break;
      case 'complete':
        overallProgress = 100;
        break;
    }

    setProgress(Math.round(overallProgress));
  }, []);

  /**
   * Generate agent from specification
   */
  const generate = useCallback(
    async (request: GenerateRequest): Promise<GenerateResponse | null> => {
      // Reset state
      setIsGenerating(true);
      setError(null);
      setCurrentStage('parsing');
      setProgress(0);
      isCancelledRef.current = false;

      const historyEntry: GenerationHistory = {
        id: `gen-${Date.now()}`,
        request,
        response: null,
        error: null,
        timestamp: Date.now(),
      };

      try {
        // Call API with progress tracking
        const response = await generateAgent(request, handleProgress);

        if (isCancelledRef.current) {
          throw new APIServiceError('Generation cancelled by user');
        }

        // Update state with result
        setLastResult(response);
        setCurrentStage('complete');
        setProgress(100);

        // Add to history
        historyEntry.response = response;
        setHistory((prev) => [historyEntry, ...prev].slice(0, 50)); // Keep last 50

        return response;
      } catch (err) {
        // Handle errors
        let errorMessage = 'Generation failed';
        let suggestion = '';

        if (err instanceof APIServiceError) {
          errorMessage = err.message;
          if (err.suggestion) {
            suggestion = err.suggestion;
          }
        } else if (err instanceof Error) {
          errorMessage = err.message;
        }

        const fullError = suggestion ? `${errorMessage}\n\n${suggestion}` : errorMessage;

        setError(fullError);
        setCurrentStage('error');
        setProgress(0);

        // Add to history with error
        historyEntry.error = fullError;
        setHistory((prev) => [historyEntry, ...prev].slice(0, 50));

        console.error('Generation error:', err);
        return null;
      } finally {
        setIsGenerating(false);
      }
    },
    [handleProgress, setHistory]
  );

  /**
   * Cancel ongoing generation
   */
  const cancel = useCallback(() => {
    isCancelledRef.current = true;
    cancelRequest();
    setIsGenerating(false);
    setCurrentStage('idle');
    setProgress(0);
    setError('Generation cancelled');
  }, []);

  /**
   * Reset state
   */
  const reset = useCallback(() => {
    setIsGenerating(false);
    setCurrentStage('idle');
    setProgress(0);
    setError(null);
    setLastResult(null);
    isCancelledRef.current = false;
  }, []);

  return {
    // State
    isGenerating,
    currentStage,
    progress,
    error,
    lastResult,

    // History
    history,
    clearHistory: () => clearHistory(),

    // Actions
    generate,
    cancel,
    reset,
  };
}

export default useGenerate;