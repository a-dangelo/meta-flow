/**
 * TypeScript types for the Chatbot API
 * These match the Pydantic models from the backend
 */

// Message types
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  confidence?: number;
}

// Workflow types
export interface WorkflowParameter {
  name: string;
  type: string;
  description?: string;
  required?: boolean;
  default?: any;
}

export interface Workflow {
  name: string;
  description: string;
  category: string;
  access_level: string;
  confidence?: number;
  parameters?: WorkflowParameter[];
}

// API Request types
export interface ChatMessageRequest {
  session_id: string;
  message: string;
  user_id?: string;
  access_level?: 'employee' | 'manager' | 'hr' | 'admin';
}

// API Response types
export interface ChatMessageResponse {
  session_id: string;
  status: 'pending' | 'collecting_parameters' | 'awaiting_user_input' |
          'ready_to_validate' | 'validated' | 'executing' | 'completed' | 'failed' | 'rejected';
  message?: string;
  matched_workflow?: string;
  search_confidence?: number;
  required_parameters?: WorkflowParameter[];
  collected_parameters?: Record<string, any>;
  pending_parameters?: string[];
  validation_errors?: string[];
  execution_result?: any;
  python_code?: string;  // Generated Python agent code for transparency
  error_message?: string;
  node_timings?: Record<string, number>;
}

export interface SessionStateResponse {
  session_id: string;
  messages: ChatMessage[];
  status: string;
  workflow?: string;
  collected_parameters?: Record<string, any>;
  python_code?: string;  // Generated Python agent code
  execution_result?: any;
  created_at: string;
  updated_at: string;
}

export interface WorkflowListResponse {
  workflows: Workflow[];
  total: number;
}

// WebSocket message types
export interface WSMessage {
  type: 'connected' | 'ping' | 'pong' | 'log' | 'status' | 'result' | 'error';
  data?: any;
}

export interface WSLogMessage extends WSMessage {
  type: 'log';
  data: {
    message: string;
    level: 'info' | 'warning' | 'error' | 'debug';
    timestamp: string;
  };
}

export interface WSStatusMessage extends WSMessage {
  type: 'status';
  data: {
    status: string;
    progress?: number;
    message?: string;
  };
}

export interface WSResultMessage extends WSMessage {
  type: 'result';
  data: {
    result: any;
    execution_time?: number;
  };
}

export interface WSErrorMessage extends WSMessage {
  type: 'error';
  data: {
    error: string;
    details?: any;
  };
}

// Store types
export interface ChatSession {
  id: string;
  messages: ChatMessage[];
  workflow?: Workflow;
  status: string;
  collectedParameters: Record<string, any>;
  pendingParameters: string[];
  executionLogs: string[];
  isConnected: boolean;
  pythonCode?: string;  // Generated Python agent code
  executionResult?: any;  // Workflow execution results
}

export interface ChatStore {
  // State
  currentSession: ChatSession | null;
  sessions: ChatSession[];
  isLoading: boolean;
  error: string | null;

  // Actions
  sendMessage: (message: string) => Promise<void>;
  createSession: () => string;
  loadSession: (sessionId: string) => Promise<void>;
  clearSession: (sessionId: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  addExecutionLog: (log: string) => void;
  updateSessionStatus: (status: string) => void;
}