/**
 * Zustand store for chat state management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { ChatMessage, ChatSession, Workflow, WorkflowParameter } from '../services/types';
import { getAPI } from '../services/api';
import type { WebSocketHandlers } from '../services/websocket';
import { getWebSocket } from '../services/websocket';

interface ChatState {
  // Current session
  currentSession: ChatSession | null;

  // Session history
  sessions: ChatSession[];

  // UI state
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;

  // Available workflows
  workflows: Workflow[];
}

interface ChatActions {
  // Session management
  createSession: () => string;
  loadSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  setCurrentSession: (session: ChatSession | null) => void;

  // Messaging
  sendMessage: (message: string) => Promise<void>;
  addMessage: (message: ChatMessage) => void;

  // Parameter handling
  updateCollectedParameters: (params: Record<string, any>) => void;
  updatePendingParameters: (params: string[]) => void;

  // Execution
  addExecutionLog: (log: string) => void;
  clearExecutionLogs: () => void;
  updateSessionStatus: (status: string) => void;

  // Workflows
  loadWorkflows: () => Promise<void>;
  selectWorkflow: (workflow: Workflow) => void;

  // UI state
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setConnected: (connected: boolean) => void;

  // Utilities
  clearError: () => void;
  reset: () => void;
}

type ChatStore = ChatState & ChatActions;

const api = getAPI();
const ws = getWebSocket();

const initialState: ChatState = {
  currentSession: null,
  sessions: [],
  isLoading: false,
  error: null,
  isConnected: false,
  workflows: [],
};

export const useChatStore = create<ChatStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,

        // Session management
        createSession: () => {
          const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const newSession: ChatSession = {
            id: sessionId,
            messages: [],
            status: 'pending',
            collectedParameters: {},
            pendingParameters: [],
            executionLogs: [],
            isConnected: false,
          };

          set((state) => ({
            currentSession: newSession,
            sessions: [...state.sessions, newSession],
            error: null,
          }));

          // Connect WebSocket
          const handlers: WebSocketHandlers = {
            onConnect: () => {
              set({ isConnected: true });
              console.log('[Store] WebSocket connected');
            },
            onDisconnect: () => {
              set({ isConnected: false });
              console.log('[Store] WebSocket disconnected');
            },
            onLog: (msg) => {
              get().addExecutionLog(msg.data.message);
            },
            onStatus: (msg) => {
              get().updateSessionStatus(msg.data.status);
            },
            onError: (msg) => {
              get().setError(msg.data.error);
            },
          };

          ws.connect(sessionId, handlers);

          return sessionId;
        },

        loadSession: async (sessionId: string) => {
          set({ isLoading: true, error: null });

          try {
            const sessionData = await api.getSession(sessionId);

            const session: ChatSession = {
              id: sessionId,
              messages: sessionData.messages,
              status: sessionData.status,
              collectedParameters: sessionData.collected_parameters || {},
              pendingParameters: [],
              executionLogs: [],
              isConnected: false,
            };

            set((state) => ({
              currentSession: session,
              sessions: state.sessions.find(s => s.id === sessionId)
                ? state.sessions
                : [...state.sessions, session],
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to load session',
              isLoading: false,
            });
          }
        },

        deleteSession: async (sessionId: string) => {
          try {
            await api.deleteSession(sessionId);

            set((state) => ({
              sessions: state.sessions.filter(s => s.id !== sessionId),
              currentSession: state.currentSession?.id === sessionId ? null : state.currentSession,
            }));

            if (ws.isConnected()) {
              ws.disconnect();
            }
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to delete session',
            });
          }
        },

        setCurrentSession: (session) => set({ currentSession: session }),

        // Messaging
        sendMessage: async (message: string) => {
          const { currentSession } = get();
          if (!currentSession) {
            set({ error: 'No active session' });
            return;
          }

          // Add user message optimistically
          const userMessage: ChatMessage = {
            role: 'user',
            content: message,
            timestamp: new Date().toISOString(),
          };

          get().addMessage(userMessage);
          set({ isLoading: true, error: null });

          try {
            const response = await api.sendMessage({
              session_id: currentSession.id,
              message,
              user_id: 'user',
              access_level: 'employee',
            });

            // Create assistant message if response has one
            const assistantMessage: ChatMessage | null = response.message ? {
              role: 'assistant',
              content: response.message,
              timestamp: new Date().toISOString(),
              confidence: response.search_confidence,
            } : null;

            // Update session with response
            set((state) => ({
              currentSession: state.currentSession ? {
                ...state.currentSession,
                messages: assistantMessage
                  ? [...state.currentSession.messages, assistantMessage]
                  : state.currentSession.messages,
                status: response.status,
                workflow: response.matched_workflow ? {
                  name: response.matched_workflow,
                  description: '',
                  category: '',
                  access_level: 'employee',
                  confidence: response.search_confidence,
                  parameters: response.required_parameters,
                } : undefined,
                collectedParameters: response.collected_parameters || {},
                pendingParameters: response.pending_parameters || [],
              } : null,
              isLoading: false,
            }));
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to send message',
              isLoading: false,
            });
          }
        },

        addMessage: (message) => {
          set((state) => ({
            currentSession: state.currentSession ? {
              ...state.currentSession,
              messages: [...state.currentSession.messages, message],
            } : null,
          }));
        },

        // Parameter handling
        updateCollectedParameters: (params) => {
          set((state) => ({
            currentSession: state.currentSession ? {
              ...state.currentSession,
              collectedParameters: { ...state.currentSession.collectedParameters, ...params },
            } : null,
          }));
        },

        updatePendingParameters: (params) => {
          set((state) => ({
            currentSession: state.currentSession ? {
              ...state.currentSession,
              pendingParameters: params,
            } : null,
          }));
        },

        // Execution
        addExecutionLog: (log) => {
          set((state) => ({
            currentSession: state.currentSession ? {
              ...state.currentSession,
              executionLogs: [...state.currentSession.executionLogs, log],
            } : null,
          }));
        },

        clearExecutionLogs: () => {
          set((state) => ({
            currentSession: state.currentSession ? {
              ...state.currentSession,
              executionLogs: [],
            } : null,
          }));
        },

        updateSessionStatus: (status) => {
          set((state) => ({
            currentSession: state.currentSession ? {
              ...state.currentSession,
              status,
            } : null,
          }));
        },

        // Workflows
        loadWorkflows: async () => {
          try {
            const response = await api.listWorkflows('employee');
            set({ workflows: response.workflows });
          } catch (error) {
            console.error('Failed to load workflows:', error);
          }
        },

        selectWorkflow: (workflow) => {
          set((state) => ({
            currentSession: state.currentSession ? {
              ...state.currentSession,
              workflow,
            } : null,
          }));
        },

        // UI state
        setLoading: (isLoading) => set({ isLoading }),
        setError: (error) => set({ error }),
        setConnected: (isConnected) => set({ isConnected }),
        clearError: () => set({ error: null }),

        // Reset store
        reset: () => {
          if (ws.isConnected()) {
            ws.disconnect();
          }
          set(initialState);
        },
      }),
      {
        name: 'chat-store',
        partialize: (state) => ({
          sessions: state.sessions.slice(-10), // Keep only last 10 sessions
        }),
      }
    ),
    {
      name: 'ChatStore',
    }
  )
);