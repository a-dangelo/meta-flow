/**
 * Custom hook for chat functionality
 */

import { useEffect, useCallback } from 'react';
import { useChatStore } from '../store/chatStore';

export function useChat() {
  const store = useChatStore();

  // Auto-create session if none exists
  useEffect(() => {
    if (!store.currentSession && store.sessions.length === 0) {
      store.createSession();
    }
  }, []);

  // Load workflows on mount
  useEffect(() => {
    if (store.workflows.length === 0) {
      store.loadWorkflows();
    }
  }, []);

  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return;

    // Ensure session exists
    if (!store.currentSession) {
      store.createSession();
      // Wait a bit for session creation
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    await store.sendMessage(message);
  }, [store.currentSession]);

  const startNewSession = useCallback(() => {
    store.createSession();
  }, []);

  const clearSession = useCallback(async () => {
    if (store.currentSession) {
      await store.deleteSession(store.currentSession.id);
    }
  }, [store.currentSession]);

  return {
    // State
    session: store.currentSession,
    messages: store.currentSession?.messages || [],
    isLoading: store.isLoading,
    error: store.error,
    isConnected: store.isConnected,
    workflows: store.workflows,
    status: store.currentSession?.status || 'pending',
    executionLogs: store.currentSession?.executionLogs || [],
    collectedParameters: store.currentSession?.collectedParameters || {},
    pendingParameters: store.currentSession?.pendingParameters || [],
    workflow: store.currentSession?.workflow,
    pythonCode: store.currentSession?.pythonCode,
    executionResult: store.currentSession?.executionResult,

    // Actions
    sendMessage,
    startNewSession,
    clearSession,
    clearError: store.clearError,
  };
}